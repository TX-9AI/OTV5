"""
notifications/telegram_sender.py  v5.1
v5.1  2026-10-26  (TG.1) — TELEGRAM NEVER BLOCKS THE TRADING LOOP, AND A FAILED ALERT IS RETRIED, NOT LOST.
      📊 MEASURED 2026-10-26, the first OTV5 paper session: 14 boxes share one bot and one chat, and at the open burst
      70 of 95 alerts failed between 09:15 and 10:00 ET — "Read timed out. (read timeout=10)" and HTTP 429 "Too Many
      Requests: retry after N". send() posted synchronously with timeout=10 and never retried, so every failed alert
      was LOST and each one STALLED THE LOOP 10 s: on SPX the bot closed a position, stalled 10 s, closed the next,
      stalled 10 s, and only then reached a Runaway hard stop, which filled at -34% against a -20% stop.
      send() now ENQUEUES to one daemon courier per process (FIFO, shared by every sender, started lazily) and returns
      at once: True = ACCEPTED for delivery, not delivered. The courier retries the SAME message — 429 after
      parameters.retry_after (fallback 5 s, cap 60 s), timeout / connection error / 5xx on backoff 2, 4, 8 ... 60 s —
      until DELIVERY_DEADLINE_S (15 min from enqueue), then logs ERROR "Telegram alert DROPPED after 15 min: ...". A 400
      "can't parse entities" is resent ONCE as plain text (no parse_mode, entities unescaped); any other 4xx except
      429/408 (a bad token or chat), or a failed plain resend, is dropped at once at ERROR. Queue bounded at 500: full
      drops the OLDEST waiting alert at ERROR; the caller never blocks. atexit drains up to 5 s. send(msg, on_result=)
      takes an optional callback, called EXACTLY ONCE per accepted message with (delivered, detail) — delivered,
      dropped at the deadline, not retryable, queue overflow, or undelivered at exit — exceptions logged, never fatal
      to the courier; disk_watch's drill and real alert take their verdict from it. send_sync() keeps the old single
      blocking POST (public, gated) and nothing in the trading loop calls it. The token is scrubbed from any logged
      exception text. Gate tests/check_telegram_queue.py T1-T12, born red on v5.0.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
Telegram delivery.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

notifications/telegram_sender.py — Telegram alerts via Bot API.
initial release, replaces sms_sender.py (Twilio)
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Credentials come from environment variables set by setup_ec2.sh.
Gracefully disabled if TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not configured.
"""

import atexit
import collections
import html
import logging
import os
import threading
import time

import requests
from config import get_telegram_token, get_telegram_chat_id, telegram_configured

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# ── v5.1 (TG.1) delivery constants. Module globals, read at USE time, so the gate
# (tests/check_telegram_queue.py) can shrink them without a sleep of 15 minutes.
REQUEST_TIMEOUT_S      = 10      # per POST; off the trading thread now, so 10 s costs no loop time
DELIVERY_DEADLINE_S    = 900     # 15 min from enqueue, then DROPPED at ERROR - never silently
QUEUE_MAX              = 500     # full -> the OLDEST waiting alert is dropped, at ERROR; the caller never blocks
RETRY_AFTER_FALLBACK_S = 5       # a 429 whose body carries no parameters.retry_after
RETRY_AFTER_CAP_S      = 60      # never trust a retry_after past a minute; the deadline still bounds the total
BACKOFF_START_S        = 2       # timeout / connection error / 5xx: 2, 4, 8 ... capped
BACKOFF_CAP_S          = 60
EXIT_DRAIN_S           = 5       # atexit: a bounded drain so a shutdown alert usually gets out


def _scrub(text: str, token: str) -> str:
    """An exception string can carry the request URL, which carries the token."""
    text = str(text)
    return text.replace(token, "<token>") if token else text


class _Item:
    """One queued alert. `done` makes its on_result fire EXACTLY ONCE, whichever of
    the courier, the overflow drop or the exit drain reaches a verdict first."""
    __slots__ = ("token", "chat_id", "text", "enq", "on_result", "done")

    def __init__(self, token, chat_id, text, on_result):
        self.token, self.chat_id, self.text = token, chat_id, text
        self.enq, self.on_result, self.done = time.time(), on_result, False


_finish_lock = threading.Lock()


def _finish(item: "_Item", delivered: bool, detail: str) -> None:
    """Report the verdict to the caller's on_result, once. Never raises: a callback
    that throws is logged and the courier carries on."""
    with _finish_lock:
        if item.done:
            return
        item.done = True
    cb = item.on_result
    if cb is None:
        return
    try:
        cb(bool(delivered), str(detail))
    except Exception as e:                                          # noqa: BLE001
        logger.error("Telegram on_result callback raised (%s: %s) for: %s",
                     type(e).__name__, _scrub(e, item.token), item.text[:80])


def _is_parse_error(code: int, body: str) -> bool:
    return code == 400 and "can't parse entities" in (body or "")


class _Courier:
    """ONE daemon worker per process, FIFO. Every TelegramSender shares it, so the
    bot's AlertManager sender and the disk guard's sender cannot race each other
    into the same 429."""

    def __init__(self):
        self._cond     = threading.Condition()
        self._q        = collections.deque()
        self._thread   = None
        self._current  = None           # the item out of the queue and in flight
        self._pid      = os.getpid()
        self._atexit   = False

    # ── caller side: never blocks on the network ────────────────────────────
    def put(self, token: str, chat_id: str, text: str, on_result=None) -> None:
        dropped = []
        with self._cond:
            while len(self._q) >= max(1, int(QUEUE_MAX)):
                old = self._q.popleft()
                dropped.append(old)
                logger.error("Telegram queue full (%d): dropped the OLDEST queued alert: %s",
                             QUEUE_MAX, old.text[:80])
            self._q.append(_Item(token, chat_id, text, on_result))
            self._ensure_worker()
            self._cond.notify_all()
        for old in dropped:                 # outside the lock: a callback may send()
            _finish(old, False, "dropped: queue full")

    def _ensure_worker(self) -> None:
        # caller holds self._cond
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="telegram-courier", daemon=True)
        self._thread.start()
        if not self._atexit:
            atexit.register(self.drain, EXIT_DRAIN_S, True)
            self._atexit = True

    def pending(self) -> int:
        with self._cond:
            return len(self._q) + (1 if self._current is not None else 0)

    def drain(self, timeout: float = EXIT_DRAIN_S, at_exit: bool = False) -> bool:
        """Wait up to `timeout` s for the queue to empty. True if it did. Never hangs.
        at_exit: whatever is left is reported undelivered to its on_result."""
        end = time.time() + max(0.0, float(timeout))
        with self._cond:
            while self._q or self._current is not None:
                left = end - time.time()
                if left <= 0 or self._thread is None or not self._thread.is_alive():
                    break
                self._cond.wait(min(left, 0.25))
            left_over = list(self._q) + ([self._current] if self._current is not None else [])
            if at_exit:
                self._q.clear()
        n = len(left_over)
        if n and at_exit:
            logger.error("Telegram: %d alert(s) NOT delivered at exit (%.0fs drain spent)", n, timeout)
            for it in left_over:
                _finish(it, False, "undelivered at exit")
        return n == 0

    # ── worker side ─────────────────────────────────────────────────────────
    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._q:
                    self._cond.wait()
                item = self._q.popleft()
                self._current = item
            try:
                ok, detail = self._deliver(item)
            except Exception as e:                                  # noqa: BLE001
                ok, detail = False, f"courier error: {_scrub(e, item.token)}"
                logger.error("Telegram courier: unexpected error, alert dropped (%s): %s",
                             detail, item.text[:80])
            _finish(item, ok, detail)
            with self._cond:
                self._current = None
                self._cond.notify_all()

    def _deliver(self, item: "_Item"):
        """-> (delivered, detail). Logs every drop at ERROR."""
        token, chat_id, text, enq = item.token, item.chat_id, item.text, item.enq
        backoff, attempt, plain = float(BACKOFF_START_S), 0, False
        while True:
            attempt += 1
            verdict, wait, why, code = _post_once(token, chat_id, text, REQUEST_TIMEOUT_S,
                                                  parse_mode=None if plain else "HTML")
            if verdict == "ok":
                if attempt > 1:
                    logger.info("Telegram delivered after %d attempts (%.0fs queued%s): %s",
                                attempt, time.time() - enq, ", as plain text" if plain else "", text[:80])
                else:
                    logger.debug("Telegram sent: %s", text[:80])
                return True, "delivered" + (" (plain text)" if plain else "")
            if verdict == "fatal":
                if not plain and _is_parse_error(code, why):
                    # TG.1 — the HTML parser refused it. The same words as PLAIN
                    # TEXT, once: an alert that reads "&lt;" beats no alert.
                    plain = True
                    text = html.unescape(text)
                    logger.warning("Telegram 400 can't parse entities; resending ONCE as plain text: %s",
                                   text[:40])
                    continue
                logger.error("Telegram alert DROPPED, not retryable (%s): %s", why, text[:80])
                return False, f"dropped: not retryable ({why[:60]})"
            if wait is None:                       # timeout / connection / 5xx
                wait = backoff
                backoff = min(backoff * 2, float(BACKOFF_CAP_S))
            left = enq + float(DELIVERY_DEADLINE_S) - time.time()
            if left <= 0:
                logger.error("Telegram alert DROPPED after %g min: %s  (last: %s, %d attempts)",
                             float(DELIVERY_DEADLINE_S) / 60, text[:80], why, attempt)
                return False, f"dropped: deadline after {attempt} attempts"
            logger.warning("Telegram send failed (%s); retry %d in %.1fs: %s",
                           why, attempt, wait, text[:40])
            time.sleep(min(wait, left))          # the last try lands AT the deadline, not past it


def _post_once(token: str, chat_id: str, text: str, timeout: float, parse_mode="HTML"):
    """One POST. -> (verdict, wait_s|None, why, status_code). verdict: ok | retry | fatal."""
    payload = {"chat_id": chat_id, "text": text[:4096]}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = requests.post(TELEGRAM_API.format(token=token), json=payload, timeout=timeout)
    except Exception as e:                                          # noqa: BLE001
        return "retry", None, _scrub(e, token), 0
    code = getattr(resp, "status_code", 0)
    if code == 200:
        return "ok", None, "200", code
    body = _scrub(getattr(resp, "text", ""), token)[:200]
    if code == 429:
        wait = None
        try:
            wait = float((resp.json().get("parameters") or {}).get("retry_after"))
        except Exception:                                           # noqa: BLE001
            wait = None
        if wait is None or wait <= 0:
            wait = float(RETRY_AFTER_FALLBACK_S)
        return "retry", min(wait, float(RETRY_AFTER_CAP_S)), f"429 {body}", code
    if 400 <= code < 500 and code != 408:
        # 400 bad request (e.g. "can't parse entities"), 401/403/404 bad token or chat:
        # the same bytes will fail the same way, so retrying only delays the queue.
        return "fatal", None, f"{code} {body}", code
    return "retry", None, f"{code} {body}", code


_courier = None
_courier_lock = threading.Lock()


def _get_courier() -> _Courier:
    global _courier
    with _courier_lock:
        # a forked child inherits the object but not the thread: give it its own
        if _courier is None or _courier._pid != os.getpid():
            _courier = _Courier()
        return _courier


def flush(timeout: float = EXIT_DRAIN_S) -> bool:
    """Wait up to `timeout` s for queued alerts to go out. True if none remain."""
    c = _courier
    return True if c is None else c.drain(timeout)


def pending() -> int:
    c = _courier
    return 0 if c is None else c.pending()


class TelegramSender:
    def __init__(self):
        self._enabled  = telegram_configured()
        self._token    = get_telegram_token()
        self._chat_id  = get_telegram_chat_id()
        if not self._enabled:
            logger.info("Telegram alerts disabled — token or chat ID not configured")

    def send(self, message: str, on_result=None) -> bool:
        """QUEUE the message for the courier and return at once. -> True when it was
        ACCEPTED for delivery (enabled and enqueued) - not a delivery verdict. A
        message that is finally not delivered is logged at ERROR by the courier
        (DROPPED ...). For a blocking verdict, use send_sync().

        on_result(delivered: bool, detail: str), when given, is called EXACTLY ONCE
        for an accepted message - delivered, dropped at the deadline, dropped as not
        retryable, dropped by a full queue, or undelivered at exit - from the
        courier thread (or the exit drain). It is NOT called when send() returns
        False: the caller already has that verdict. An exception it raises is
        logged and swallowed; it never stops the courier."""
        if not self._enabled:
            logger.debug(f"Telegram (disabled): {message}")
            return False
        try:
            _get_courier().put(self._token, self._chat_id, str(message), on_result)
            return True
        except Exception as e:                                      # noqa: BLE001
            logger.error(f"Telegram enqueue failed: {_scrub(e, self._token)}")
            return False

    def send_sync(self, message: str, timeout: float = REQUEST_TIMEOUT_S) -> bool:
        """The pre-v5.1 send: ONE blocking POST on the caller's thread, no retry.
        -> True iff Telegram answered 200. For drills and credential checks that
        need a delivery verdict off the trading loop; NOTHING in the loop calls it."""
        if not self._enabled:
            logger.debug(f"Telegram (disabled): {message}")
            return False
        verdict, _w, why, _c = _post_once(self._token, self._chat_id, str(message), timeout)
        if verdict == "ok":
            logger.debug(f"Telegram sent: {str(message)[:80]}")
            return True
        logger.error(f"Telegram send failed: {why}")
        return False
