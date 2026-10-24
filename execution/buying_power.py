"""
execution/buying_power.py  v1.0
v1.0  2026-10-05  r473 / F5 — A LIVE ENTRY IS NOT POSTED IF THE ACCOUNT CANNOT PAY FOR IT.

🔴 THE GAP, from OTV4TEST's live-readiness audit (F5) and measured on mainline:
no live entry path read the account's buying power. Nothing in otv4 called
Account.get_balances. An entry the account could not carry went to the broker
anyway, to be rejected there (or, on a margin account, to over-commit it), and
the boxes share one account (operator, B1: "multiple boxes will trade that
account"), so one box cannot see what the others have already spent.

THE CHECK, one place for the four live entry paths (single leg, standing ORB
offer, butterfly, credit vertical), called right after B2's clear_to_post:
  · affordable(need_usd, session, account, what) -> (ok, why)
    reads AccountBalance.derivative_buying_power (a Decimal on the boxes' SDK,
    tastytrade 13.0.0, measured on UNH 2026-10-05) through sdk_result (B0:
    get_balances is a coroutine) and refuses when need_usd exceeds it.
  · UNREADABLE BALANCES REFUSE THE POST — the same direction B2 chose for an
    unreadable order status. An entry nobody can show is affordable is not
    sent. Pages ONCE per episode and re-arms on the next good read (WA §17).
⚠️ NECESSARY, NOT SUFFICIENT: two boxes can both read the same free balance in
the same second and both post. The broker remains the final word; this stops
the case where the account visibly cannot pay.
⚠️ OPERATOR RULING: LIVE ORDERS ONLY. Paper never calls this module.
"""
import logging

from data.tasty_client import sdk_result

logger = logging.getLogger(__name__)

_PAGED: set = set()          # episode kinds already paged: "short", "unreadable"


def _page(kind: str, text: str) -> None:
    if kind in _PAGED:
        return
    _PAGED.add(kind)
    try:
        from notifications.alert_manager import get_alert_manager
        get_alert_manager()._send(text)
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[bp] page not sent (%s): %s", exc, text)


def available(session, account):
    """The account's derivative buying power in dollars, or None if unreadable."""
    try:
        bal = sdk_result(account.get_balances(session))
        v = getattr(bal, "derivative_buying_power", None)
        return float(v) if v is not None else None
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[bp] balances unreadable: %s: %s", type(exc).__name__, exc)
        return None


def affordable(need_usd: float, session, account, what: str) -> tuple:
    """(ok, why). Refuses when the need exceeds buying power, or when buying
    power cannot be read."""
    need = float(need_usd or 0.0)
    have = available(session, account)
    if have is None:
        _page("unreadable", f"⚠️ BUYING POWER unreadable — {what} not posted "
                            f"(${need:,.0f} needed). Entries refuse until it reads.")
        return False, "buying power unreadable"
    _PAGED.discard("unreadable")
    if need > have:
        _page("short", f"⚠️ BUYING POWER short — {what} not posted: needs "
                       f"${need:,.0f}, account has ${have:,.0f}.")
        return False, f"needs ${need:,.0f}, buying power ${have:,.0f}"
    _PAGED.discard("short")
    return True, f"needs ${need:,.0f} of ${have:,.0f}"


def reset() -> None:
    _PAGED.clear()
