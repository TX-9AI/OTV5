"""
notifications/telegram_sender.py  v4.0
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

import logging
import requests
from config import get_telegram_token, get_telegram_chat_id, telegram_configured

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramSender:
    def __init__(self):
        self._enabled  = telegram_configured()
        self._token    = get_telegram_token()
        self._chat_id  = get_telegram_chat_id()
        if not self._enabled:
            logger.info("Telegram alerts disabled — token or chat ID not configured")

    def send(self, message: str) -> bool:
        if not self._enabled:
            logger.debug(f"Telegram (disabled): {message}")
            return False
        try:
            url  = TELEGRAM_API.format(token=self._token)
            resp = requests.post(url, json={
                "chat_id":    self._chat_id,
                "text":       message[:4096],
                "parse_mode": "HTML",
            }, timeout=10)
            if resp.status_code == 200:
                logger.debug(f"Telegram sent: {message[:80]}")
                return True
            else:
                logger.error(
                    f"Telegram send failed: {resp.status_code} {resp.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
