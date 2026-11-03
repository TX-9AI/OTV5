#!/usr/bin/env python3
"""
tests/check_feed_session_release.py  v5.1
v5.1  2026-11-03  OTV5 r70 (3): the recursive resolvers answer one node at a time while the zone's Route 53 nameservers
      answer the set, and 54.204.44.247 is no longer a dxlink node (timed out 11-02 evening, TLS failed 11-03):
  S19 the seed is 129.153.134.53, 184.195.238.144 and 52.6.43.252 (observed 2026-11-03); 54.204.44.247 is not in it
  S21 every lookup also asks the authoritative nameservers (a local UDP server plays the system resolver and the
      zone's nameserver, with compressed answer names): the extra node follows the recursive answer, order kept; the
      NS set is cached (one NS query for two lookups); NodeBook's default resolver is _resolve_nodes; with the
      nameservers down the recursive answer stands alone, bounded, no raise; a garbage reply parses to []
v5.0  2026-11-02  OTV5 r70 (FEED.13) — new. RELEASE THE OLD, ALWAYS: THE CANDLE FEED REUSES ITS QUOTE TOKEN ACROSS
      RECONNECTS, CLOSES THE OLD SOCKET BEFORE IT OPENS A NEW ONE, AND WAITS 120-180 s AFTER A SESSION-LIMIT REFUSAL.
      2026-11-02 09:30 ET: one DXLink drop on 8 boxes, then AMZN/GOOGL/TSLA refused "The number of user sessions has
      exceeded the configured limit" on every ~60 s retry for 10-25+ minutes; the SDK minted a new quote token on every
      retry. Born red on 2ee301d at S1-S20 (no QuoteTokenCache / SessionReleasingStreamer / session_limit_wait; run() opens the
      SDK's DXLinkStreamer, which GETs /api-quote-tokens on every open).

DRIVEN THROUGH THE REAL run() AND THE REAL SDK _reader/_heartbeat: tastytrade's DXLinkStreamer protocol code talks to a
fake httpx2 client/socket (cf.AsyncClient patched), the session is a fake whose _get counts /api-quote-tokens calls,
and run()'s asyncio.sleep is recorded (cf.asyncio proxied) and ends the run after N reconnects. No network, no box.

  S1  three reconnects after drops/refusals fetch the quote token ONCE and every AUTH carries that same token
  S2  each socket is closed before the next one is opened (strict open/close alternation; none left open)
  S3  before any session-limit refusal a drop waits the unchanged jittered ladder (3 s rung, never below 3); the
      refusal waits [120, 180] s and logs exactly one SESSION_LIMIT line naming the wait; the drops after it, with no
      successful connection between, are held in the lockout ([200, 300] s), not put back on the 3 -> 60 s ladder
  S4  the token is refreshed once it is older than QUOTE_TOKEN_MAX_AGE_S (19 h: reused; 21 h: fetched)
  S5  DXLink answering AUTH with UNAUTHORIZED, or ERROR UNAUTHORIZED, drops the token: the next connect fetches anew
  S6  no AUTHORIZED within AUTH_TIMEOUT_S drops the token and reconnects (socket closed)
  S7  a socket left open by its context manager is closed by the streamer's own release (logged, still alternating)
  S8  session_limit_wait: 500 draws in [120, 180], spread > 30 s; _is_session_limit matches the incident text
      (bare and inside an ExceptionGroup) and not WebSocketNetworkError / "no candle subscriptions succeeded"
  S9  the token string never appears in any log record
  S10 a FRESH process refused at its first attempt never takes a 3/6/12 s rung: every wait from the first refusal
      until a connection succeeds (subscriptions live) is in [120, 300] (first [120, 180]), including a drop inside
      the lockout; the successful connection clears it and the next drops wait the 3 -> 60 s ladder again
  THE LIMIT IS PER DXLINK NODE (2026-11-02 10:50 ET: AMZN/GOOGL refused 85 min on 129.153.134.53, connected at once
  pinned to the AWS nodes 184.195.238.144 / 54.204.44.247):
  S11 a box whose last good node is A, refused on A, dials node B next; B connects and is kept; SESSION_LIMIT names A
  S12 every pinned dial carries Host and sni_hostname = the URL's hostname and the client gets no verify override; a
      REAL TLS probe (local server, openssl cert for dxlink.test, dialled at 127.0.0.1 through _pinned_target) connects
      with the right name (server sees SNI and Host dxlink.test) and is refused with a wrong one - verification is on
  S13 DNS fallback: no node known -> the plain URL with no Host/SNI override; only the refused node known -> dialled
  S14 A records from repeated lookups accumulate and persist in dxlink_nodes.json beside the feed store
  S15 with no last good node a stable crc32(symbol) spreads 14 symbols over all 3 known nodes; a last good node is kept
  The operator, 2026-11-02: "Yes, connect to a known new server & if we can probe to spread out our connections prior to
  the open, it might be worth looking into."
  S16 a refusal with an un-cooled alternate known redials a NEW node in 1-5 s (twice: three refusals, three nodes);
      once every node is cooled the 120-180 s hold applies
  S17 PRE-OPEN: the choice is crc32(symbol) over the nodes that pass a probe, stickiness ignored (14 symbols use all 3;
      an unreachable node is never picked); in RTH the last good node is kept; run() dials the hashed node before the
      open; a node whose TLS is fine but whose upgrade answers 502 (129.153.134.53 from 14:19 ET 11-02) is never
      picked. The REAL _probe_node against local TLS servers (cert for dxlink.test; 127.0.0.1 answers 101, 127.0.0.2
      on the same port answers 502): 101 / 502 / None for a wrong SNI name (verification on); the server receives
      exactly ONE bare upgrade request (GET /realtime, Host dxlink.test, nothing after it - no SETUP, no AUTH, no
      token) and then EOF; a pre-open choose() over both never picks the 502 node, even as the last good node
  S18 the FLEET list (warehouse/s3_push.py share_dxlink_nodes, fake S3): this box's book is put once (not again when
      unchanged; no cooling fields shared; non-IPs dropped), every box's object is merged per node (newest timestamps,
      the symbols that know it; a corrupt object skipped) into dxlink_nodes_fleet.json, a feed NodeBook reads it; the
      call is after the PAUSE gate, outside the stage loop and never added to total_pushed / total_failed
  S19 the 11-02 nodes come from data/dxlink_nodes_seed.json (observed 2026-11-02) and are candidates; no IPv4 literal
      is in an executable string of candle_feed.py or s3_push.py
  S20 a websocket upgrade answered 502 at connect time cools that node (5 min) and redials another known node in
      1-5 s with one UPGRADE_REFUSED line naming the node and the status; the next node connects
"""
import asyncio
import contextlib
import logging
import os
import random
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_TMP = tempfile.mkdtemp(prefix="feedsess_")
os.environ["OT_FEED_DB"] = os.path.join(_TMP, "feed_store.db")
os.environ["OT_FEED_MAINT_FLAG"] = os.path.join(_TMP, "NO_MAINT")
os.environ["OT_FEED_MODE"] = "service"
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


UPGRADE502 = "UPGRADE502"   # the fake node answers the websocket upgrade "HTTP/1.1 502 Bad Gateway"
DELAY = "DELAY"          # the fake socket idles 0.5 s (lets run() finish subscribing) before its next item
UNAUTH = {"type": "AUTH_STATE", "channel": 0, "state": "UNAUTHORIZED"}
AUTHED = {"type": "AUTH_STATE", "channel": 0, "state": "AUTHORIZED"}
LIMIT = {"type": "ERROR", "channel": 0, "error": "UNKNOWN",
         "message": "The number of user sessions has exceeded the configured limit"}


class _Records(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class World:
    """One fake TastyTrade: a session that mints tokens, a client whose sockets play scripts."""

    def __init__(self, cf, scripts, leaky=False):
        import anyio
        self.anyio, self.cf = anyio, cf
        self.scripts = [s if isinstance(s, str) else list(s) for s in scripts]
        self.leaky = leaky
        self.events, self.auth_tokens, self.urls = [], [], []
        self.minted = 0
        self.dials, self.client_kwargs, self.probes = [], [], []
        self.open_now = 0
        world = self

        class Session:
            client_kwargs = {}

            async def _get(self, url):
                assert url == "/api-quote-tokens", url
                world.minted += 1
                return {"dxlink-url": "wss://fake-dxlink/%d" % world.minted,
                        "token": "SECRET-TOKEN-%d-xyz" % world.minted}

        class WS:
            def __init__(self, n, script):
                self.n, self.script, self.inject = n, script, []
                self._should_close = anyio.Event()

            async def send_json(self, message):
                if message.get("type") == "AUTH":
                    world.auth_tokens.append(message.get("token"))
                if message.get("type") == "CHANNEL_REQUEST":       # the server opens every channel asked for
                    self.inject.append({"type": "CHANNEL_OPENED", "channel": message["channel"]})

            async def receive_json(self):
                await anyio.sleep(0)
                while True:
                    if self.inject:
                        return self.inject.pop(0)
                    if not self.script:
                        await anyio.sleep_forever()
                    if self.script[0] == DELAY:
                        self.script.pop(0)
                        await anyio.sleep(0.5)
                        continue
                    break
                item = self.script.pop(0)
                if isinstance(item, BaseException):
                    raise item
                return item

            async def close(self):
                if not self._should_close.is_set():
                    world.events.append(("close", self.n))
                    world.open_now -= 1
                self._should_close.set()

        class Client:
            def __init__(self, **kw):
                world.client_kwargs.append(dict(kw))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            @contextlib.asynccontextmanager
            async def websocket(self, url, keepalive_ping_interval_seconds=None, headers=None, extensions=None):
                world.urls.append(url)
                world.dials.append((url, dict(headers or {}), dict(extensions or {})))
                n = len(world.urls)
                script = world.scripts.pop(0) if world.scripts else []
                if script == UPGRADE502:
                    from httpx2.websockets import WebSocketUpgradeError

                    class _Resp:
                        status_code = 502
                    raise WebSocketUpgradeError(_Resp())
                world.events.append(("open", n))
                world.open_now += 1
                world.max_open = max(getattr(world, "max_open", 0), world.open_now)
                ws = WS(n, script)
                try:
                    yield ws
                finally:
                    if not world.leaky:
                        with anyio.CancelScope(shield=True):
                            await ws.close()

        self.Session, self.Client = Session, Client


def mkbook(cf, path, **kw):
    """A NodeBook isolated from the repo's seed and any fleet file unless the test names them."""
    kw.setdefault("fleet_path", os.path.join(_TMP, "no_fleet.json"))
    kw.setdefault("seed_path", os.path.join(_TMP, "no_seed.json"))
    return cf.NodeBook(path=path, **kw)


def drive(cf, scripts, stops, leaky=False, on_sleep=None, auth_timeout=None, dns=None, book=None, preopen=False,
          probe=None):
    """Run the real CandleFeed.run() against the fake world until `stops` reconnect sleeps. Returns (world, waits, log)."""
    world = World(cf, scripts, leaky=leaky)
    waits = []
    rec = _Records()
    lg = logging.getLogger()
    lg.addHandler(rec)
    lg.setLevel(logging.DEBUG)

    class _AsyncioProxy:
        def __getattr__(self, name):
            return getattr(asyncio, name)

        @staticmethod
        async def sleep(s, *a, **k):
            waits.append(float(s))
            if on_sleep:
                on_sleep(len(waits))
            if len(waits) >= stops:
                raise asyncio.CancelledError()
            await asyncio.sleep(0)

    saved = (cf.AsyncClient, cf.get_session, cf.asyncio, cf._QUOTE_TOKENS, cf.AUTH_TIMEOUT_S, cf._OPEN_WS["ws"],
             cf._NODES, cf._preopen)
    clock = {"t": 1_000_000.0}
    session = world.Session()
    try:
        cf.AsyncClient = world.Client
        cf.get_session = lambda: session
        cf.asyncio = _AsyncioProxy()
        cf._QUOTE_TOKENS = cf.QuoteTokenCache(clock=lambda: clock["t"])
        cf._OPEN_WS["ws"] = None
        dns_calls = {"n": 0}

        async def _fake_dns(host, port):                    # dns: list of IPs, or a list of per-call lists
            dns_calls["n"] += 1
            if dns and isinstance(dns[0], list):
                return list(dns[min(dns_calls["n"], len(dns)) - 1])
            return list(dns or [])
        cf._NODES = book if book is not None else mkbook(cf, path=os.path.join(_TMP, "nodes_%d.json" % id(world)),
                                                              clock=lambda: clock["t"], resolver=_fake_dns)
        if book is not None:
            book.resolver, book.clock = _fake_dns, (lambda: clock["t"])

        async def _fake_probe(ip, host, port, **kw):
            world.probes.append(ip)
            return 101 if probe is None else probe(ip)
        cf._NODES.prober = _fake_probe
        cf._preopen = (lambda *a, **k: True) if preopen else (lambda *a, **k: False)
        if auth_timeout is not None:
            cf.AUTH_TIMEOUT_S = auth_timeout
        world.clock = clock
        feed = cf.CandleFeed(cf.FeedStore(os.environ["OT_FEED_DB"]))
        try:
            asyncio.run(feed.run())
        except (asyncio.CancelledError, BaseExceptionGroup) as e:     # the recorded sleep ends the run
            if not isinstance(e, asyncio.CancelledError):
                raise
    finally:
        (cf.AsyncClient, cf.get_session, cf.asyncio, cf._QUOTE_TOKENS, cf.AUTH_TIMEOUT_S, cf._OPEN_WS["ws"],
         cf._NODES, cf._preopen) = saved
        lg.removeHandler(rec)
    return world, waits, rec.lines


def alternates(events):
    want = []
    for i in range(1, len(events) // 2 + 1):
        want += [("open", i), ("close", i)]
    return events == want


def _time_now():
    import time
    return time.time()


def _tls_probe(cf):
    """A real httpx2 GET to 127.0.0.1 through _pinned_target with a cert for dxlink.test: the right name connects
    (and the server sees SNI and Host = dxlink.test), a wrong name fails verification. 'ok' or the reason."""
    import ssl
    import subprocess
    d = tempfile.mkdtemp(prefix="tls_", dir=_TMP)
    key, crt = os.path.join(d, "k.pem"), os.path.join(d, "c.pem")
    try:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt,
                        "-days", "2", "-subj", "/CN=dxlink.test", "-addext", "subjectAltName=DNS:dxlink.test"],
                       check=True, capture_output=True, timeout=60)
    except Exception as e:                                              # noqa: BLE001
        return "openssl unavailable: %s" % e
    seen = {}

    async def go():
        import httpx2
        sctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sctx.load_cert_chain(crt, key)
        def _sni(sock, name, ctx):
            seen.setdefault("sni", name)                          # the first (right-name) handshake
            return None                                          # None = carry on (an int would abort the handshake)
        sctx.sni_callback = _sni

        async def handle(r, w_):
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = await r.read(4096)
                if not chunk:
                    break
                data += chunk
            for line in data.split(b"\r\n"):
                if line.lower().startswith(b"host:"):
                    seen.setdefault("host", line.split(b":", 1)[1].strip().decode())
            w_.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            await w_.drain()
            w_.close()
        srv = await asyncio.start_server(handle, "127.0.0.1", 0, ssl=sctx)
        port = srv.sockets[0].getsockname()[1]
        cctx = ssl.create_default_context(cafile=crt)          # verify ON: the default context, trusting the test cert
        try:
            url, hdr, ext = cf._pinned_target("https://dxlink.test:%d/realtime" % port, "127.0.0.1")
            async with httpx2.AsyncClient(verify=cctx) as c:
                resp = await c.get(url, headers=hdr, extensions=ext)
                good = resp.status_code == 200 and resp.text == "ok"
            bad_url, bad_hdr, bad_ext = cf._pinned_target("https://wrong.test:%d/realtime" % port, "127.0.0.1")
            refused = False
            try:
                async with httpx2.AsyncClient(verify=cctx) as c:
                    await c.get(bad_url, headers=bad_hdr, extensions=bad_ext)
            except Exception as e:                                      # noqa: BLE001
                refused = "certificate" in str(e).lower() or "hostname" in str(e).lower() or "verify" in str(e).lower()
            return good, refused, url
        finally:
            srv.close()
            await srv.wait_closed()
    try:
        good, refused, url = asyncio.run(go())
    except Exception as e:                                              # noqa: BLE001
        return "probe error: %s: %s" % (type(e).__name__, e)
    if not (good and refused and url.startswith("https://127.0.0.1:") and seen.get("sni") == "dxlink.test"
            and seen.get("host", "").split(":")[0] == "dxlink.test"):
        return "good=%s wrong-name-refused=%s url=%s seen=%s" % (good, refused, url, seen)
    return "ok"


def _probe_check(cf):
    """The REAL cf._probe_node and NodeBook.choose against local TLS servers with a cert for dxlink.test: 127.0.0.1
    answers the upgrade 101, 127.0.0.2 (same port) completes TLS and answers 502 - the 11-02 14:19 ET shape. The probe
    returns 101 / 502 / None for a wrong SNI name (verification on); the server receives exactly ONE bare upgrade
    request (GET /realtime, Host dxlink.test, nothing after it: no SETUP, no AUTH, no token) and then EOF; and a
    pre-open choose() over both nodes never picks the 502 node for any of 14 symbols. 'ok' or the reason."""
    import ssl
    import subprocess
    d = tempfile.mkdtemp(prefix="probe_", dir=_TMP)
    key, crt = os.path.join(d, "k.pem"), os.path.join(d, "c.pem")
    try:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt,
                        "-days", "2", "-subj", "/CN=dxlink.test", "-addext", "subjectAltName=DNS:dxlink.test"],
                       check=True, capture_output=True, timeout=60)
    except Exception as e:                                              # noqa: BLE001
        return "openssl unavailable: %s" % e
    reqs, tails = [], []
    syms = ["SPX", "QQQ", "AMZN", "GOOGL", "TSLA", "UNH", "NVDA", "SOFI", "CRM", "CVX", "NFLX", "AMD", "AVGO", "META"]

    async def go():
        sctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sctx.load_cert_chain(crt, key)

        def handler(status):
            async def handle(r, w_):
                data = b""
                try:
                    while b"\r\n\r\n" not in data:
                        chunk = await asyncio.wait_for(r.read(4096), timeout=2.0)
                        if not chunk:
                            break
                        data += chunk
                except Exception:                                       # noqa: BLE001
                    pass
                reqs.append(data)
                if status == 101:
                    w_.write(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
                else:
                    w_.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                await w_.drain()
                try:
                    tails.append(await asyncio.wait_for(r.read(4096), timeout=2.0))
                except Exception:                                       # noqa: BLE001
                    tails.append(b"(no EOF)")
                w_.close()
            return handle
        good = await asyncio.start_server(handler(101), "127.0.0.1", 0, ssl=sctx)
        port = good.sockets[0].getsockname()[1]
        bad = await asyncio.start_server(handler(502), "127.0.0.2", port, ssl=sctx)
        cctx = ssl.create_default_context(cafile=crt)
        try:
            c_good = await cf._probe_node("127.0.0.1", "dxlink.test", port, path="/realtime", ssl_context=cctx)
            c_bad = await cf._probe_node("127.0.0.2", "dxlink.test", port, path="/realtime", ssl_context=cctx)
            c_name = await cf._probe_node("127.0.0.1", "wrong.test", port, path="/realtime", ssl_context=cctx)
            picks = set()
            for sym in syms:
                b = mkbook(cf, path=os.path.join(d, "book_%s.json" % sym))
                b._load()["nodes"].update({"127.0.0.1": {"seen": _time_now()}, "127.0.0.2": {"seen": _time_now()}})
                b._data["last_ok"] = "127.0.0.2"                         # stickiness must not save the 502 node

                async def r(h, p_):
                    return []

                async def pr(ip, h, p_, path="/", _c=cctx):
                    return await cf._probe_node(ip, h, p_, path=path, ssl_context=_c)
                b.resolver, b.prober = r, pr
                picks.add((await b.choose("dxlink.test", port, sym, preopen=True, path="/realtime"))[0])
            await asyncio.sleep(0.3)
            return c_good, c_bad, c_name, picks
        finally:
            for srv in (good, bad):
                srv.close()
                await srv.wait_closed()
    try:
        c_good, c_bad, c_name, picks = asyncio.run(go())
    except Exception as e:                                              # noqa: BLE001
        return "probe error: %s: %s" % (type(e).__name__, e)
    first = reqs[0] if reqs else b""
    one_req = (first.startswith(b"GET /realtime HTTP/1.1\r\n") and b"\r\nHost: dxlink.test\r\n" in first
               and b"\r\nUpgrade: websocket\r\n" in first and first.endswith(b"\r\n\r\n")
               and first.count(b"\r\n\r\n") == 1 and not any(w in first.upper() for w in (b"AUTH", b"SETUP", b"TOKEN")))
    if not (c_good == 101 and c_bad == 502 and c_name is None and one_req
            and all(len(x) > 0 and x == x.split(b"\r\n\r\n")[0] + b"\r\n\r\n" for x in reqs)
            and tails and all(t == b"" for t in tails) and picks == {"127.0.0.1"}):
        return "101-node=%s 502-node=%s wrong-name=%s request=%r tails=%s picks=%s" % (
            c_good, c_bad, c_name, first[:120], tails, picks)
    return "ok"


def _share_check(cf, A, B, C):
    import ast
    import json
    sys.path.insert(0, os.path.join(ROOT, "warehouse"))
    try:
        import importlib
        s3p = importlib.import_module("warehouse.s3_push")
    except Exception as e:                                              # noqa: BLE001
        return False, "import warehouse.s3_push: %s: %s" % (type(e).__name__, e)
    d = tempfile.mkdtemp(prefix="share_", dir=_TMP)
    T = float(int(_time_now()))
    with open(os.path.join(d, "dxlink_nodes.json"), "w") as fh:
        json.dump({"nodes": {A: {"seen": T - 400, "ok": T - 400, "refused": T - 401}, "not-an-ip": {"seen": T}},
                   "last_ok": A}, fh)

    class Body:
        def __init__(self, b):
            self.b = b

        def read(self):
            return self.b

    class FakeS3:
        def __init__(self):
            self.objs = {
                "fleet/dxlink_nodes/sym=AMZN.json": json.dumps({"sym": "AMZN", "nodes": {B: {"ok": T - 300}}}).encode(),
                "fleet/dxlink_nodes/sym=TSLA.json": json.dumps({"sym": "TSLA", "nodes": {C: {"seen": T - 200},
                                                                                       A: {"seen": T - 350}}}).encode(),
                "fleet/dxlink_nodes/sym=JUNK.json": b"{not json",
            }
            self.puts = []

        def put_object(self, Bucket, Key, Body):
            self.puts.append(Key)
            self.objs[Key] = Body

        def get_object(self, Bucket, Key):
            return {"Body": Body(self.objs[Key])}

        def get_paginator(self, name):
            outer = self

            class P:
                def paginate(self, Bucket, Prefix):
                    yield {"Contents": [{"Key": k} for k in sorted(outer.objs) if k.startswith(Prefix)]}
            return P()
    saved = s3p.NODES_SHARED_SHA
    s3p.NODES_SHARED_SHA = os.path.join(d, "shared.sha")
    try:
        fake = FakeS3()
        n1 = s3p.share_dxlink_nodes(fake, "bucket", "QQQ", data_dir=d)
        n2 = s3p.share_dxlink_nodes(fake, "bucket", "QQQ", data_dir=d)
    finally:
        s3p.NODES_SHARED_SHA = saved
    fleet = json.load(open(os.path.join(d, "dxlink_nodes_fleet.json")))["nodes"]
    mine = json.loads(fake.objs.get("fleet/dxlink_nodes/sym=QQQ.json", b"{}"))
    book = mkbook(cf, path=os.path.join(d, "feed_book.json"), fleet_path=os.path.join(d, "dxlink_nodes_fleet.json"))
    cands = book.candidates() if hasattr(book, "candidates") else []
    # the share is outside the stage loop and never added to total_pushed / total_failed, and a PAUSED main() returns
    # before it (static: the call sits after the pause gate and outside `for name, fn in stages`)
    src = open(os.path.join(ROOT, "warehouse", "s3_push.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    mainf = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n for n in ast.walk(mainf) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "share_dxlink_nodes"]
    loops = [n for n in ast.walk(mainf) if isinstance(n, ast.For) and getattr(n.iter, "id", "") == "stages"]
    in_loop = any(c in list(ast.walk(lp)) for lp in loops for c in calls)
    counted = any(isinstance(n, ast.AugAssign) and getattr(n.target, "id", "") in ("total_pushed", "total_failed")
                  and any(isinstance(v, ast.Name) and v.id in ("_nn", "_no") for v in ast.walk(n.value))
                  for n in ast.walk(mainf))
    pause_line = next(n.lineno for n in ast.walk(mainf) if isinstance(n, ast.If)
                      and "PAUSE_FLAG" in ast.unparse(n.test))
    ok = (fake.puts.count("fleet/dxlink_nodes/sym=QQQ.json") == 1 and set(mine.get("nodes", {})) == {A}
          and "refused" not in json.dumps(mine) and n1 == (3, 3) and n2[0] == 3
          and set(fleet) == {A, B, C} and fleet[A]["seen"] == T - 350 and fleet[A]["ok"] == T - 400
          and fleet[A]["by"] == ["QQQ", "TSLA"] and fleet[B]["by"] == ["AMZN"]
          and cands == sorted([A, B, C]) and len(calls) == 1 and not in_loop and not counted
          and pause_line < calls[0].lineno)
    return ok, ("puts=%s mine=%s n=%s/%s fleet=%s cands=%s calls=%d in_loop=%s counted=%s"
                % (fake.puts, mine, n1, n2, fleet, cands, len(calls), in_loop, counted))


def _seed_check(cf, A, B, C):
    import ast
    import json
    import re
    seed = os.path.join(ROOT, "data", "dxlink_nodes_seed.json")
    try:
        d = json.load(open(seed))
        nodes = set(d.get("nodes", {}))
    except Exception as e:                                              # noqa: BLE001
        return False, "seed unreadable: %s" % e
    book = cf.NodeBook(path=os.path.join(_TMP, "nodes_S19.json"), fleet_path=os.path.join(_TMP, "no_fleet.json"))
    cands = set(book.candidates())
    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    found = []
    for rel in ("data/candle_feed.py", "warehouse/s3_push.py"):
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body \
                    and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
                docs.add(id(n.body[0].value))
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and ip_re.search(n.value):
                found.append((rel, n.lineno, n.value[:40]))
    want = {"129.153.134.53", "184.195.238.144", "52.6.43.252"}           # r70 (3): 54.204.44.247 removed 2026-11-03
    ok = nodes == want and "54.204.44.247" not in nodes and d.get("observed") == "2026-11-03" and want <= cands \
        and not found
    return ok, "seed=%s observed=%s cands=%s literals=%s" % (sorted(nodes), d.get("observed"), sorted(cands), found)


def _auth_dns_check(cf):
    """S21: the authoritative nameservers are asked too (a local UDP DNS server plays the system resolver AND the zone's
    nameserver; the answer names are compressed pointers)."""
    import socket as _s
    import struct
    import threading
    import time as _t
    host = "dxlink.test"
    seen = {"NS": 0, "A": 0}
    srv = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    stop = threading.Event()

    def name_end(buf, off):
        while buf[off]:
            off += 1 + buf[off]
        return off + 1

    def serve():
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                q, addr = srv.recvfrom(512)
            except Exception:                                           # noqa: BLE001
                continue
            qid = struct.unpack(">H", q[:2])[0]
            qend = name_end(q, 12)
            qtype = struct.unpack(">H", q[qend:qend + 2])[0]
            qname = q[12:qend]
            question = q[12:qend + 4]
            ans = b""
            n = 0
            if qtype == 2 and qname == b"\x06dxlink\x04test\x00":
                seen["NS"] += 1
                rd = b"\x09localhost\x00"
                ans = b"\xc0\x0c" + struct.pack(">HHIH", 2, 1, 60, len(rd)) + rd
                n = 1
            elif qtype == 1 and qname == b"\x06dxlink\x04test\x00":
                seen["A"] += 1
                for ip in ((10, 0, 0, 1), (10, 0, 0, 2)):
                    ans += b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 60, 4) + bytes(ip)
                    n += 1
            hdr = struct.pack(">HHHHHH", qid, 0x8180, 1, n, 0, 0)
            srv.sendto(hdr + question + ans, addr)

    th = threading.Thread(target=serve, daemon=True)
    th.start()
    saved = (cf.NODE_DNS_PORT, cf._system_nameservers, cf._resolve_v4)
    try:
        cf.NODE_DNS_PORT = port
        cf._system_nameservers = lambda: ["127.0.0.1"]
        cf._AUTH_NS_CACHE.update(host=None, ns=[], at=0.0)

        async def rec(h, p):
            return ["10.0.0.9", "10.0.0.2"]
        cf._resolve_v4 = rec
        got = asyncio.run(cf._resolve_nodes(host, 443))
        ns_after_first = seen["NS"]
        got2 = asyncio.run(cf._resolve_nodes(host, 443))            # NS set cached: no second NS query
        default_ok = cf.NodeBook(path=os.path.join(_TMP, "nodes_S21.json")).resolver is cf._resolve_nodes
        # the authoritative path down: the recursive answer stands alone, no raise, bounded
        stop.set()
        th.join(1.0)
        srv.close()
        cf._AUTH_NS_CACHE.update(host=None, ns=[], at=0.0)
        t0 = _t.monotonic()
        down = asyncio.run(cf._resolve_nodes(host, 443))
        took = _t.monotonic() - t0
        bad = cf._dns_parse(b"\x00\x01" + b"\x00" * 3, 1, 1)             # a short/garbage reply parses to []
    finally:
        cf.NODE_DNS_PORT, cf._system_nameservers, cf._resolve_v4 = saved
        cf._AUTH_NS_CACHE.update(host=None, ns=[], at=0.0)
        stop.set()
    ok = (got == ["10.0.0.9", "10.0.0.2", "10.0.0.1"] and got2 == got and ns_after_first == 1 and seen["NS"] == 1
          and seen["A"] == 2 and default_ok and down == ["10.0.0.9", "10.0.0.2"]
          and took <= cf.NODE_DNS_TIMEOUT_S + 1.5 and bad == [])
    return ok, "got=%s again=%s queries=%s default=%s down=%s took=%.1fs bad=%s" % (
        got, got2, seen, default_ok, down, took, bad)


def main():
    try:
        import data.candle_feed as cf
        from httpx2.websockets import WebSocketNetworkError
        from tastytrade.utils import TastytradeError
        need = ("QuoteTokenCache", "SessionReleasingStreamer", "session_limit_wait", "_is_session_limit",
                "QUOTE_TOKEN_MAX_AGE_S", "AsyncClient", "_QUOTE_TOKENS", "_OPEN_WS", "NodeBook", "_NODES",
                "_pinned_target", "_nodes_path", "node_switch_wait", "_probe_node", "_preopen",
                "_upgrade_status", "_resolve_nodes", "_resolve_authoritative", "_dns_parse")
        missing = [n for n in need if not hasattr(cf, n)]
    except Exception as e:                                              # noqa: BLE001
        cf, missing = None, ["import: %s: %s" % (type(e).__name__, e)]
    if missing:
        for n in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14", "S15",
                  "S16", "S17", "S18", "S19", "S20", "S21"):
            check("%s (FEED.13 not present)" % n, False, "missing %s" % missing)
        print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
        return 1

    def drop():
        return WebSocketNetworkError()

    all_lines = []

    # ── Run A: drop, session-limit refusal, drop, drop ───────────────────────────────────────────────────────
    w, waits, lines = drive(cf, [[UNAUTH, AUTHED, drop()], [UNAUTH, LIMIT], [UNAUTH, AUTHED, drop()],
                                 [UNAUTH, AUTHED, drop()]], stops=4)
    all_lines += lines
    check("S1 four connects fetch the quote token once and every AUTH carries it",
          w.minted == 1 and len(w.auth_tokens) == 4 and len(set(w.auth_tokens)) == 1,
          "minted=%d auth tokens=%d distinct=%d" % (w.minted, len(w.auth_tokens), len(set(w.auth_tokens))))
    check("S2 each socket closed before the next opens; none left open",
          alternates(w.events) and len(w.events) == 8 and w.open_now == 0 and w.max_open == 1,
          "events=%s open_now=%d" % (w.events, w.open_now))
    sl = [x for x in lines if x.startswith("SESSION_LIMIT")]
    ok3 = (len(waits) == 4 and 3.0 <= waits[0] <= 3.6 + 1e-9 and 120.0 <= waits[1] <= 180.0
           and 200.0 <= waits[2] <= 300.0 and 200.0 <= waits[3] <= 300.0
           and len(sl) == 1 and ("%.1fs" % waits[1]) in sl[0]
           and sum("feed stream error" in x for x in lines) == 3
           and sum("lockout held" in x for x in lines) == 2)
    check("S3 ladder before a refusal; the refusal waits [120,180] with one SESSION_LIMIT line; drops after it stay held",
          ok3,
          "waits=%s SESSION_LIMIT lines=%s" % ([round(x, 2) for x in waits], sl))

    # ── Run B: expiry — 19 h reused, 21 h refreshed ─────────────────────────────────────────────────────────
    holder = {}

    def on_sleep(n):
        holder["w"].clock["t"] += {1: 19 * 3600, 2: 2 * 3600}.get(n, 0)

    _orig_world = World

    class _Hook(World):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            holder["w"] = self
    globals()["World"] = _Hook
    try:
        w, waits, lines = drive(cf, [[UNAUTH, AUTHED, drop()]] * 3, stops=3, on_sleep=on_sleep)
    finally:
        globals()["World"] = _orig_world
    all_lines += lines
    toks = w.auth_tokens
    check("S4 token reused at 19 h, refreshed past QUOTE_TOKEN_MAX_AGE_S (21 h)",
          cf.QUOTE_TOKEN_MAX_AGE_S == 20 * 3600 and w.minted == 2 and len(toks) == 3
          and toks[0] == toks[1] != toks[2],
          "minted=%d tokens=%s" % (w.minted, [t[-5:] if t else t for t in toks]))

    # ── Run C: auth reject (AUTH_STATE UNAUTHORIZED after AUTH; ERROR UNAUTHORIZED) ─────────────────────────
    # The ERROR's message carries no auth words, so only the socket watch (its `error` field) can catch it; the
    # state path must be caught at once, not by the AUTH timeout (both runs are bounded to 10 s below).
    import time as _t
    t0 = _t.monotonic()
    w1, waits1, l1 = drive(cf, [[UNAUTH, UNAUTH], [UNAUTH, AUTHED, drop()]], stops=2)
    err = {"type": "ERROR", "channel": 0, "error": "UNAUTHORIZED", "message": "Access denied"}
    w2, waits2, l2 = drive(cf, [[UNAUTH, err], [UNAUTH, AUTHED, drop()]], stops=2)
    fast = _t.monotonic() - t0 < 10.0
    all_lines += l1 + l2
    check("S5 an AUTH rejected (UNAUTHORIZED again, or ERROR UNAUTHORIZED) drops the token; the next connect fetches",
          w1.minted == 2 and len(set(w1.auth_tokens)) == 2 and w2.minted == 2 and len(set(w2.auth_tokens)) == 2
          and alternates(w1.events) and alternates(w2.events) and waits1[0] < 120 and waits2[0] < 120 and fast,
          "state-path minted=%d err-path minted=%d waits=%s/%s fast=%s" % (w1.minted, w2.minted, waits1, waits2,
                                                                          fast))

    # ── Run D: no AUTHORIZED within AUTH_TIMEOUT_S ──────────────────────────────────────────────────────────
    w, waits, lines = drive(cf, [[UNAUTH], [UNAUTH, AUTHED, drop()]], stops=2, auth_timeout=0.3)
    all_lines += lines
    check("S6 no AUTHORIZED within AUTH_TIMEOUT_S drops the token and reconnects with the socket closed",
          w.minted == 2 and alternates(w.events) and w.open_now == 0 and cf.AUTH_TIMEOUT_S == 45.0,
          "minted=%d events=%s" % (w.minted, w.events))

    # ── Run E: a context manager that leaves the socket open ────────────────────────────────────────────────
    w, waits, lines = drive(cf, [[UNAUTH, AUTHED, drop()], [UNAUTH, AUTHED, drop()]], stops=2, leaky=True)
    all_lines += lines
    check("S7 a socket left open is closed by the streamer's own release before the next opens",
          alternates(w.events) and w.open_now == 0 and any("still open" in x for x in lines),
          "events=%s open_now=%d" % (w.events, w.open_now))

    # ── S8: the wait and the classifier ─────────────────────────────────────────────────────────────────────
    r = random.Random(5)
    draws = [cf.session_limit_wait(rng=r) for _ in range(500)]
    later = [cf.session_limit_wait(n, rng=r) for n in (1, 2, 5, 50) for _ in range(200)]
    inc = TastytradeError("Fatal streamer error: The number of user sessions has exceeded the configured limit")
    grp = ExceptionGroup("unhandled errors in a TaskGroup", [inc])
    neg = [WebSocketNetworkError(), RuntimeError("WouldBlock"), RuntimeError("no candle subscriptions succeeded"),
           ExceptionGroup("g", [WebSocketNetworkError()])]
    check("S8 session_limit_wait in [120,180] and spread; the classifier matches the refusal and nothing else",
          all(120.0 <= d <= 180.0 for d in draws) and max(draws) - min(draws) > 30
          and all(120.0 <= d <= 300.0 for d in later) and max(later) - min(later) > 30
          and cf._is_session_limit(inc) and cf._is_session_limit(grp)
          and not any(cf._is_session_limit(x) for x in neg),
          "min %.1f max %.1f" % (min(draws), max(draws)))

    # ── Run F: a fresh process refused at its first attempt ──────────────────────────────────────────────────
    w, waits, lines = drive(cf, [[UNAUTH, LIMIT], [UNAUTH, LIMIT], [UNAUTH, AUTHED, drop()], [UNAUTH, LIMIT],
                                 [UNAUTH, AUTHED, DELAY, drop()], [UNAUTH, AUTHED, drop()]], stops=6)
    all_lines += lines
    held, after = waits[:4], waits[4:]
    cleared = any("lockout cleared" in x for x in lines)
    check("S10 fresh process: every wait from the first refusal to a live connection is >= 120 s; success clears it",
          len(waits) == 6 and 120.0 <= held[0] <= 180.0 and all(120.0 <= x <= 300.0 for x in held)
          and min(held) >= cf.SESSION_LIMIT_WAIT_MIN_S and cleared
          and 3.0 <= after[0] <= 3.6 + 1e-9 and 4.8 - 1e-9 <= after[1] <= 7.2 + 1e-9
          and sum(x.startswith("SESSION_LIMIT:") for x in lines) == 3 and w.minted == 1,
          "waits=%s cleared=%s minted=%d" % ([round(x, 1) for x in waits], cleared, w.minted))

    # ── Node runs (FEED.13 part 2): the session limit is per dxlink node ───────────────────────────────────
    A, B, C = "129.153.134.53", "184.195.238.144", "54.204.44.247"

    def host_of(url):
        return url.split("//", 1)[1].split("/", 1)[0].split(":")[0]

    # Run G: this box's last good node is A; A refuses; the next dial goes to B; B connects; B is kept.
    bk = mkbook(cf, path=os.path.join(_TMP, "nodes_G.json"))
    bk._load()["nodes"].update({A: {"seen": 1_000_000.0, "ok": 1_000_000.0}})
    bk._data["last_ok"] = A
    w, waits, lines = drive(cf, [[UNAUTH, LIMIT], [UNAUTH, AUTHED, DELAY, drop()], [UNAUTH, AUTHED, drop()]],
                            stops=3, dns=[A, B], book=bk)
    all_lines += lines
    dialled = [host_of(u) for u in w.urls]
    sl = [x for x in lines if x.startswith("SESSION_LIMIT:")]
    check("S11 refused on node A -> node B is redialled within 1-5 s (not the 120 s hold); B connects and is kept; "
          "SESSION_LIMIT names node A and the switch",
          dialled == [A, B, B] and len(sl) == 1 and ("node %s" % A) in sl[0] and "switching" in sl[0]
          and 1.0 <= waits[0] <= 5.0
          and any(("connected on dxlink node %s" % B) in x for x in lines)
          and sum(("dxlink node %s for" % ip) in x for x in lines for ip in (A, B)) == 3,
          "dialled=%s waits=%s SESSION_LIMIT=%s" % (dialled, waits, sl))

    sni_ok = all(h.get("Host") == "fake-dxlink" and e.get("sni_hostname") == "fake-dxlink" for _, h, e in w.dials)
    no_verify_kw = all("verify" not in kw for kw in w.client_kwargs)
    tls = _tls_probe(cf)
    check("S12 a pinned dial keeps the hostname for SNI and Host, verify stays on (real TLS: right name connects, "
          "wrong name refused)", sni_ok and no_verify_kw and tls == "ok",
          "dials=%s client kwargs=%s tls=%s" % (w.dials[:2], w.client_kwargs[:1], tls))

    # Run H: DNS fallback - nothing resolves and nothing known -> the plain URL; only A known and A refused -> A again.
    w1, _, l1 = drive(cf, [[UNAUTH, AUTHED, drop()], [UNAUTH, AUTHED, drop()]], stops=2, dns=[])
    w2, waits2, l2 = drive(cf, [[UNAUTH, LIMIT], [UNAUTH, AUTHED, drop()]], stops=2, dns=[A])
    all_lines += l1 + l2
    check("S13 DNS fallback: no node known -> the plain URL, no Host/SNI override; only the refused node known -> "
          "dialled again by DNS",
          w1.urls == ["wss://fake-dxlink/1"] * 2 and all(not h and not e for _, h, e in w1.dials)
          and [host_of(u) for u in w2.urls] == [A, A]
          and any("dns (no usable alternate known)" in x for x in l2) and 120.0 <= waits2[0] <= 180.0
          and any("no other node known, holding" in x for x in l2),
          "plain=%s single=%s" % (w1.urls, w2.urls))

    # S14: A records from repeated lookups accumulate and persist beside the feed store; a new book reads them.
    p14 = os.path.join(_TMP, "nodes_S14.json")
    b14 = mkbook(cf, path=p14)
    w, _, _ = drive(cf, [[UNAUTH, AUTHED, drop()]] * 3, stops=3, dns=[[A], [B], [C]], book=b14)
    again = mkbook(cf, path=p14)
    known = sorted(again._load()["nodes"])
    default_path = cf._nodes_path()
    check("S14 every A record seen over repeated lookups is kept and persisted next to the feed store",
          known == sorted([A, B, C]) and os.path.dirname(default_path) == os.path.dirname(
              os.path.abspath(os.environ["OT_FEED_DB"])) and default_path.endswith("dxlink_nodes.json"),
          "known=%s default=%s" % (known, default_path))

    # S15: steady-state spread - with no last good node, the symbol's hash picks among the known nodes; a symbol is
    # stable and 14 symbols use every node; a box with a last good node stays on it.
    fleet = ["SPX", "QQQ", "AMZN", "GOOGL", "TSLA", "UNH", "NVDA", "SOFI", "CRM", "CVX", "NFLX", "AMD", "AVGO", "META"]

    def pick(sym, last=None):
        b = mkbook(cf, path=os.path.join(_TMP, "nodes_S15_%s.json" % sym))
        async def r(h, p):
            return [A]
        b.resolver = r
        b._load()["nodes"].update({ip: {"seen": _time_now()} for ip in (A, B, C)})
        if last:
            b._data["last_ok"] = last
        return asyncio.run(b.choose("fake-dxlink", 443, sym))[0]
    picks = {s_: pick(s_) for s_ in fleet}
    check("S15 spread: a stable symbol hash over the known nodes uses every node across 14 symbols; a last good node "
          "is kept", set(picks.values()) == {A, B, C} and all(pick(s_) == picks[s_] for s_ in fleet[:4])
          and all(pick(s_, last=A) == A for s_ in fleet[:4]),
          "picks=%s" % picks)

    # ── S16: immediate switch while alternates last; the hold only when none is left ───────────────────────────────
    bk = mkbook(cf, path=os.path.join(_TMP, "nodes_S16.json"))
    bk._load()["nodes"].update({ip: {"seen": 1_000_000.0} for ip in (A, B, C)})
    bk._data["last_ok"] = A
    w, waits, lines = drive(cf, [[UNAUTH, LIMIT], [UNAUTH, LIMIT], [UNAUTH, LIMIT], [UNAUTH, AUTHED, drop()]],
                            stops=3, dns=[A], book=bk)
    all_lines += lines
    dialled = [host_of(u) for u in w.urls]
    sl = [x for x in lines if x.startswith("SESSION_LIMIT:")]
    check("S16 each refusal with an un-cooled alternate redials a NEW node in 1-5 s; with every node cooled the "
          "120-180 s hold applies",
          len(waits) == 3 and 1.0 <= waits[0] <= 5.0 and 1.0 <= waits[1] <= 5.0 and 120.0 <= waits[2] <= 180.0
          and dialled[:3][0] == A and len(set(dialled[:3])) == 3
          and sum("switching to another known node" in x for x in sl) == 2
          and sum("no other node known, holding" in x for x in sl) == 1,
          "dialled=%s waits=%s" % (dialled, [round(x, 1) for x in waits]))

    # ── S17: pre-open spread (stickiness ignored, unreachable skipped), RTH stickiness, and a real TLS-only probe ───
    def pick_open(sym, preopen, reach=(A, B, C), last=A, bad502=()):
        b = mkbook(cf, path=os.path.join(_TMP, "nodes_S17_%s_%s.json" % (sym, preopen)))
        b._load()["nodes"].update({ip: {"seen": _time_now()} for ip in (A, B, C)})
        b._data["last_ok"] = last
        async def r(h, p):
            return [A]
        async def pr(ip, h, p, **kw):
            return 502 if ip in bad502 else (101 if ip in reach else None)
        b.resolver, b.prober = r, pr
        return asyncio.run(b.choose("fake-dxlink", 443, sym, preopen=preopen))
    pre = {s_: pick_open(s_, True)[0] for s_ in fleet}
    rth = {s_: pick_open(s_, False)[0] for s_ in fleet}
    two = {s_: pick_open(s_, True, reach=(A, B))[0] for s_ in fleet}
    gw = {s_: pick_open(s_, True, bad502=(B,))[0] for s_ in fleet}      # B: TLS fine, upgrade answered 502
    want_qqq = sorted([A, B, C])[__import__("zlib").crc32(b"QQQ") % 3]
    last_for_run = next(ip for ip in (A, B, C) if ip != want_qqq)
    bk = mkbook(cf, path=os.path.join(_TMP, "nodes_S17_run.json"))
    bk._load()["nodes"].update({ip: {"seen": 1_000_000.0} for ip in (A, B, C)})
    bk._data["last_ok"] = last_for_run
    w, _, lines = drive(cf, [[UNAUTH, AUTHED, drop()]], stops=1, dns=[A], book=bk, preopen=True)
    all_lines += lines
    probe = _probe_check(cf)
    check("S17 pre-open: the symbol hash over USABLE nodes (upgrade answered 101), stickiness ignored (14 symbols use all "
          "3; an unreachable node or one answering 502 is never picked); in RTH the last good node is kept; run() dials "
          "the hashed node; the real probe sends one bare upgrade and reads only the status line",
          set(pre.values()) == {A, B, C} and set(rth.values()) == {A} and C not in set(two.values())
          and set(two.values()) == {A, B} and set(gw.values()) == {A, C} and [host_of(u) for u in w.urls] == [want_qqq]
          and sorted(w.probes) == sorted([A, B, C]) and any("pre-open probe: 3/3" in x for x in lines)
          and probe == "ok",
          "pre=%s rth=%s two=%s gw=%s dial=%s probes=%s probe=%s" % (
              sorted(set(pre.values())), sorted(set(rth.values())), sorted(set(two.values())),
              sorted(set(gw.values())), w.urls, w.probes, probe))

    # ── S20: a 502 at connect time cools the node and switches at once ─────────────────────────────────────────────
    bk = mkbook(cf, path=os.path.join(_TMP, "nodes_S20.json"))
    bk._load()["nodes"].update({ip: {"seen": 1_000_000.0} for ip in (A, B)})
    bk._data["last_ok"] = A
    w, waits, lines = drive(cf, [UPGRADE502, [UNAUTH, AUTHED, DELAY, drop()]], stops=2, dns=[A], book=bk)
    all_lines += lines
    ur = [x for x in lines if x.startswith("UPGRADE_REFUSED:")]
    a_cool = bk._cool_until(A) > w.clock["t"]
    check("S20 a websocket upgrade answered 502 at connect cools that node 5 min and redials another known node in "
          "1-5 s; the next one connects",
          [host_of(u) for u in w.urls] == [A, B] and 1.0 <= waits[0] <= 5.0 and len(ur) == 1
          and ("node %s" % A) in ur[0] and "HTTP 502" in ur[0] and a_cool
          and any(("connected on dxlink node %s" % B) in x for x in lines) and w.minted == 1,
          "dialled=%s waits=%s lines=%s cooled=%s" % ([host_of(u) for u in w.urls], waits, ur, a_cool))

    # ── S18: the fleet-shared list (warehouse/s3_push.py) ─────────────────────────────────────────────────────────
    check("S18 the fleet list: each box's book is put (only when changed), every box's is merged into "
          "dxlink_nodes_fleet.json, the feed reads it, and the DRAIN accounting and a PAUSED box are untouched",
          *_share_check(cf, A, B, C))

    # ── S19: the seed is data, never code ────────────────────────────────────────────────────────────────────────
    check("S19 the 11-02 nodes are seeded from data/dxlink_nodes_seed.json, and no IPv4 literal is in executable code",
          *_seed_check(cf, A, B, C))

    # ── S21: the authoritative nameservers are asked too ──────────────────────────────────────────────────────────
    check("S21 every lookup also asks the zone's authoritative nameservers (found through the system resolver, the "
          "host first; NS set cached 1 h); their extra nodes follow the recursive answer, order kept; the NodeBook's "
          "default resolver is _resolve_nodes; with the nameservers down the recursive answer stands, bounded, no raise",
          *_auth_dns_check(cf))

    leaked = [x for x in all_lines if "SECRET-TOKEN" in x]
    check("S9 the token never appears in a log record", not leaked and len(all_lines) > 0, "leaked: %s" % leaked[:2])

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(rc)
