#!/usr/bin/env python3
"""
tests/check_feed_fractional_size.py  v5.0
v5.0  2026-10-28  OTV5 r47 (FEED.12) — A FRACTIONAL SHARE SIZE REACHES `prints` AND `last_trade`.
      tastytrade 13.2.3 types `size` as int on TimeAndSale (int | None on Trade); dxFeed sends fractional shares
      (0.419652), pydantic raised int_from_float and the SDK SKIPPED the event (Event.from_stream and
      DXLinkStreamer._map_message catch the ValidationError and log "Failed to parse event ... skipping").
      MEASURED 2026-10-27: about half of QQQ's TimeAndSale events (~0.3% of volume) never reached `prints`.
      Driven through the REAL SDK parse path (DXLinkStreamer._map_message, both the COMPACT and the FULL data
      format) and the REAL writer (CandleFeed._on_time_and_sale / _on_trade -> FeedStore.append_prints /
      append_last_trade) into a scratch store.

  F0  the premise: this SDK types TimeAndSale.size as int and Trade.size as int | None (else this is moot)
  F1  COMPACT TimeAndSale with size 0.419652 is parsed (not skipped), the size preserved exactly
  F2  FULL-format TimeAndSale with size 0.419652 is parsed, the size preserved exactly
  F3  COMPACT Trade with size 0.419652 is parsed, the size preserved exactly
  F4  whole-number sizes still parse: TimeAndSale 100 -> 100, Trade 300 -> 300, Trade NaN size -> None
  F5  no "Failed to parse event" line for these events (the FEED.4 filter goes quiet for this class)
  F6  the prints writer stores 0.419652 in prints.size (REAL), and the Trade writer in last_trade.size
  F7  data.candle_feed.FRACTIONAL_SIZE reports both models "ok" (what main() logs at start)

Run against the SDK the boxes use (requirements.lock: tastytrade==13.2.3); the version is printed.
Born red on b78fc8f at F1, F2, F3, F5, F6 and F7.
Run:  python3 tests/check_feed_fractional_size.py
"""
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import typing
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_s = tempfile.mkdtemp(prefix="check_feed_fractional_size.")
os.environ["OT_FEED_DB"] = os.path.join(_s, "feed.db")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
FAILED = []
FRAC = 0.419652


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.msgs = []

    def emit(self, record):
        self.msgs.append(record.getMessage())


class _Sink:
    def __init__(self):
        self.got = []

    def send_nowait(self, ev):
        self.got.append(ev)


def tas_values(keys, size):
    d = {k: None for k in keys}
    d.update(event_symbol="QQQ", event_time=0, event_flags=0, index=7_000_000_001, time=1_761_573_600_000,
             time_nano_part=0, sequence=11, exchange_code="Q", price="611.25", size=size, bid_price="611.24",
             ask_price="611.26", trade_through_exempt="X", aggressor_side="BUY", spread_leg=False,
             extended_trading_hours=False, valid_tick=True, type="NEW")
    return [d[k] for k in keys]


def trade_values(keys, size):
    d = {k: None for k in keys}
    d.update(event_symbol="QQQ", event_time=0, time=1_761_573_600_000, time_nano_part=0, sequence=12,
             exchange_code="Q", day_id=20388, tick_direction="UP", extended_trading_hours=False, price="611.25",
             change="1.5", size=size, day_volume="1000.5", day_turnover="611250")
    return [d[k] for k in keys]


def parse(cls, name, message):
    """The SDK's own _map_message, on a minimal streamer: one channel, a sink for its queue."""
    from tastytrade.streamer import DXLinkStreamer
    sink = _Sink()
    fake = SimpleNamespace(_channels_reversed={1: name}, _send={name: sink})
    DXLinkStreamer._map_message(fake, message, 1)
    return sink.got


def main():
    import tastytrade
    from tastytrade.dxfeed import TimeAndSale, Trade
    print(f"tastytrade {tastytrade.VERSION} at {os.path.dirname(tastytrade.__file__)}")
    tas_ann, tr_ann = TimeAndSale.model_fields["size"].annotation, Trade.model_fields["size"].annotation
    check("F0 premise: the SDK types TimeAndSale.size int and Trade.size int | None",
          tas_ann is int and set(typing.get_args(tr_ann)) == {int, type(None)}, f"{tas_ann!r} / {tr_ann!r}")

    cap = _Cap(); tl = logging.getLogger("tastytrade"); tl.addHandler(cap); tl.setLevel(logging.DEBUG)
    import data.candle_feed as CF                      # the fix (if any) applies at this import
    tas_keys, tr_keys = list(TimeAndSale.model_fields), list(Trade.model_fields)

    got1 = parse(TimeAndSale, "TimeAndSale", ["TimeAndSale", tas_values(tas_keys, FRAC)])
    check("F1 COMPACT TimeAndSale size 0.419652 is parsed with its size", len(got1) == 1 and
          float(got1[0].size) == FRAC, f"parsed={[g.size for g in got1]}")

    full = dict(zip(tas_keys, tas_values(tas_keys, FRAC)))
    full = {TimeAndSale.model_fields[k].alias or k: v for k, v in full.items()}
    got2 = parse(TimeAndSale, "TimeAndSale", [full])
    check("F2 FULL TimeAndSale size 0.419652 is parsed with its size", len(got2) == 1 and
          float(got2[0].size) == FRAC, f"parsed={[g.size for g in got2]}")

    got3 = parse(Trade, "Trade", ["Trade", trade_values(tr_keys, FRAC)])
    check("F3 COMPACT Trade size 0.419652 is parsed with its size", len(got3) == 1 and
          float(got3[0].size) == FRAC, f"parsed={[g.size for g in got3]}")
    fails = [m for m in cap.msgs if "Failed to parse event" in m]
    n_frac_fail = len(fails)

    w1 = parse(TimeAndSale, "TimeAndSale", ["TimeAndSale", tas_values(tas_keys, 100)])
    w2 = parse(Trade, "Trade", ["Trade", trade_values(tr_keys, 300) + trade_values(tr_keys, "NaN")])
    check("F4 whole sizes still parse: TimeAndSale 100, Trade 300, Trade NaN -> None",
          [float(g.size) for g in w1] == [100.0] and len(w2) == 2 and float(w2[0].size) == 300.0
          and w2[1].size is None, f"tas={[g.size for g in w1]} trade={[g.size for g in w2]}")
    check("F5 no 'Failed to parse event' for the fractional events", n_frac_fail == 0,
          f"{n_frac_fail} parse failure line(s)" + (f": {fails[0][:110]}" if fails else ""))
    tl.removeHandler(cap)

    store = CF.FeedStore(os.environ["OT_FEED_DB"])
    feed = CF.CandleFeed(store)
    for ev in got1:
        feed._on_time_and_sale(ev)
    for ev in got3:
        feed._on_trade(ev)
    store.append_prints(feed._prints_buf)
    store.append_last_trade(feed._trade_buf)
    store.conn.commit()
    con = sqlite3.connect(os.environ["OT_FEED_DB"])
    pr = con.execute("SELECT size, typeof(size) FROM prints WHERE symbol='QQQ'").fetchall()
    lt = con.execute("SELECT size, typeof(size) FROM last_trade WHERE symbol='QQQ'").fetchall()
    con.close()
    check("F6 prints.size and last_trade.size store 0.419652 (REAL)",
          pr == [(FRAC, "real")] and lt == [(FRAC, "real")], f"prints={pr} last_trade={lt}")

    fs = getattr(CF, "FRACTIONAL_SIZE", None)
    check("F7 candle_feed.FRACTIONAL_SIZE reports both models ok",
          fs == {"TimeAndSale": "ok", "Trade": "ok"}, f"{fs}")

    store.close()
    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
