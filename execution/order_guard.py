"""
execution/order_guard.py  v1.1
v1.1  2026-10-20  r495 / B4 — A RESTART CANCELS ITS INSTRUMENT'S LEFTOVER WORKING ORDERS BEFORE IT
      POSTS. The suspects below are in memory, and B1 adopts POSITIONS, not working orders, so a
      restart while an entry was working at the broker forgot it and the next tick could post the
      same intent again: two positions. sweep_working() lists the account's live orders, keeps
      the ones this box still tracks (a resting offer's id, an open row's live_exit_state
      order_id / last_order_id), and cancels every other WORKING order of this box's instrument
      family (SPX = SPX + SPXW), paging the count. Run at LIVE boot before the broker reconcile
      (main._recover_open_position), and again from clear_to_post until it has come back clean:
      NO LIVE ENTRY POSTS IN A PROCESS UNTIL ONE SWEEP HAS. A failed read, a failed cancel or an
      unreadable kept-id set blocks entries (never closes) and pages once. Clean means every
      cancelled id READ DEAD within CANCEL_CONFIRM_S (5 s, heartbeat touched while polling) and
      no order of the instrument sits in Cancel/Replace Requested; a leftover that FILLED is
      paged by id, and blocks entries when OT_BROKER_RECONCILE is off (nothing would adopt it).
      condor_roll's roll and tent ask clear_to_post BEFORE their first leg (whole adjustment or
      none). get_live_orders lists SIMPLE orders: nothing here posts a complex order. Critiqued by
      OTV4TEST (MSG-QQQ-1020-18). The client order id
      (external_identifier) stays deferred (operator 10-20). Operator: "Go ahead & build it".
      GATE tests/check_boot_order_sweep.py.
v1.0  2026-10-04  r466 / B2 — AN ORDER THAT WAS SENT IS NEVER FORGOTTEN BY AN ERROR.

🔴 THE DEFECT, found by OTV4TEST's live-readiness audit and measured on mainline:
every live entry path (single leg, butterfly, standing ORB offer, credit
vertical) calls place_order and then confirms, records or polls. If ANYTHING
raised after place_order returned, the except handler logged "order failed"
and returned nothing: the rung was not refused, the order id was dropped, and
no working-order record existed — so the next tick posted the SAME intent
again while the first order might still fill. A double position the DB never
sees.

THE GUARD, one place for all four paths:
  · after_failure(key, placed, session, account, what) — called from the except
    handler whenever an order WAS placed: it tries to CANCEL that order, records
    it as SUSPECT for this intent, and pages once.
  · clear_to_post(key, session, account) — called BEFORE posting for an intent:
    if a suspect order exists it reads its status from the broker. Dead
    (cancelled / expired / removed / rejected) -> cleared, post. Still working
    -> do NOT post. FILLED -> do NOT post, page once: the fill is real but
    unrecorded, and broker reconcile adopts it. Unreadable -> do NOT post.
⚠️ IN-MEMORY. A restart forgets the suspects; at restart the broker reconcile
(B1) adopts any position that exists, and (r495) sweep_working cancels the
instrument's untracked working orders before anything posts. Paper never places, so this is inert there.
"""
import json
import logging
import os
import time

from data.tasty_client import sdk_result

logger = logging.getLogger(__name__)

_SUSPECT: dict = {}          # intent key -> {"order_id", "ts", "what", "paged_fill"}
_BOOT: dict = {"state": None, "why": "", "paged": False}   # r495 B4: None = not swept yet


def _page(text: str) -> None:
    try:
        from notifications.alert_manager import get_alert_manager
        get_alert_manager()._send(text)
    except Exception:                                          # noqa: BLE001
        pass


def _status_name(placed) -> str:
    st = getattr(placed, "status", None)
    return str(getattr(st, "name", st) or "").upper()


_DEAD = {"CANCELLED", "EXPIRED", "REMOVED", "PARTIALLY_REMOVED", "REJECTED"}


def after_failure(key: str, placed, session, account, what: str) -> None:
    """An order WAS placed and something after it raised. Cancel it, remember
    it, page. Never raises."""
    oid = str(getattr(placed, "id", "") or "") if placed is not None else ""
    if not oid:
        return
    cancelled = False
    try:
        sdk_result(account.delete_order(session, oid))
        cancelled = True
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[guard] %s: cancel of %s after an error failed: %s", what, oid, exc)
    _SUSPECT[key] = {"order_id": oid, "ts": time.time(), "what": what, "paged_fill": False}
    logger.error("[guard] %s: order %s was PLACED and then an error followed — "
                 "cancel %s; this intent posts nothing until the broker says "
                 "the order is dead", what, oid, "requested" if cancelled else "FAILED")
    _page(f"⚠️ ORDER GUARD — {what}: order {oid} was placed, then an error. Cancel "
          f"{'requested' if cancelled else 'FAILED'}; no re-post until it is confirmed dead.")


# r495 / B4 — the states a working (cancellable) order reads, normalised: tastytrade's
# OrderStatus values "Received", "Routed", "In Flight", "Live", "Contingent" (the same set
# tools/emergency_watchdog.LIVE_STATES cancels).
_WORKING = {"RECEIVED", "ROUTED", "IN_FLIGHT", "LIVE", "CONTINGENT"}
# Working too, but already on their way out: never re-cancelled, never read as a clean book.
_PENDING = {"CANCEL_REQUESTED", "REPLACE_REQUESTED"}
_DEAD_N = {"CANCELLED", "EXPIRED", "REMOVED", "PARTIALLY_REMOVED", "REJECTED"}
CANCEL_CONFIRM_S = 5.0
_POLL_S = 0.25


def _norm_status(o) -> str:
    st = getattr(o, "status", None)
    v = getattr(st, "value", None) or getattr(st, "name", None) or st
    return str(v or "").upper().replace(" ", "_")


def _kept_order_ids() -> set:
    """Order ids this box still tracks across a restart: today's WORKING resting offers and
    every open row's live_exit_state order ids (B3). Raises when the rows are unreadable —
    the caller then cancels NOTHING and blocks entries."""
    keep = set()
    from execution import resting_orders as _ro
    from utils.time_utils import now_et
    for r in _ro.working(now_et().strftime("%Y-%m-%d")):
        if r.get("order_id"):
            keep.add(str(r["order_id"]))
    from database.trade_logger import get_trade_logger
    for r in get_trade_logger().get_open_trades():
        raw = r.get("live_exit_state")
        if not raw:
            continue
        try:
            st = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for k in ("order_id", "last_order_id"):
            if st.get(k):
                keep.add(str(st[k]))
    return keep


def _of_instrument(o, family: set) -> bool:
    if str(getattr(o, "underlying_symbol", "") or "").upper() in family:
        return True
    for lg in (getattr(o, "legs", None) or []):
        sym = str(getattr(lg, "symbol", "") or "").strip()
        if sym and sym.split()[0].upper() in family:
            return True
    return False


def sweep_working(session, account, instrument: str = "") -> tuple:
    """r495 / B4. Cancel this instrument's working orders the box no longer tracks.
    (ok, cancelled, why). ok=False: entries stay blocked. Never raises."""
    from data.tasty_client import _underlying_family
    inst = instrument or os.environ.get("OT_INSTRUMENT", "")
    fam = _underlying_family(inst)
    cancelled, failed, kept = [], [], 0
    try:
        if not inst:
            raise ValueError("no OT_INSTRUMENT")
        keep = _kept_order_ids()
        orders = sdk_result(account.get_live_orders(session)) or []
    except Exception as exc:                                   # noqa: BLE001
        return _boot_result(False, 0, f"working orders unread ({type(exc).__name__}: {exc})")
    pending = []
    for o in orders:
        if not _of_instrument(o, fam):
            continue
        if _norm_status(o) in _PENDING:
            pending.append(f"{getattr(o, 'id', '?')} {_norm_status(o)}")
            continue
        if _norm_status(o) not in _WORKING:
            continue
        oid = str(getattr(o, "id", "") or "")
        if not oid:
            continue
        if oid in keep:
            kept += 1
            continue
        try:
            sdk_result(account.delete_order(session, oid))
            cancelled.append(oid)
            logger.warning("[guard] boot sweep: cancelled leftover working order %s (%s)",
                           oid, _norm_status(o))
        except Exception as exc:                               # noqa: BLE001
            failed.append(oid)
            logger.error("[guard] boot sweep: cancel of %s FAILED: %s", oid, exc)
    if failed:
        return _boot_result(False, len(cancelled),
                            f"cancel FAILED for {', '.join(failed)}; cancelled {len(cancelled)}")
    open_ids, filled = _confirm_dead(session, account, cancelled)
    blockers = []
    if filled:
        try:
            from config import BROKER_RECONCILE_ENABLED as _rec
        except Exception:                                      # noqa: BLE001
            _rec = False
        _page(f"🔴 ORDER GUARD [{inst}] — leftover working order(s) {', '.join(filled)} FILLED "
              f"before the cancel: a position the DB did not record. "
              + ("Broker reconcile adopts it." if _rec else
                 "OT_BROKER_RECONCILE is OFF — nothing adopts it; entries stay blocked."))
        if not _rec:
            blockers.append(f"{', '.join(filled)} FILLED and reconcile is off")
    if open_ids:
        blockers.append(f"cancel not confirmed in {CANCEL_CONFIRM_S:g}s for {', '.join(open_ids)}")
    if pending:
        blockers.append(f"still pending: {', '.join(pending)}")
    if blockers:
        return _boot_result(False, len(cancelled), "; ".join(blockers))
    return _boot_result(True, len(cancelled),
                        f"cancelled {len(cancelled)}, kept {kept} tracked")


def _confirm_dead(session, account, ids: list) -> tuple:
    """Poll each cancelled id until it reads dead, bounded by CANCEL_CONFIRM_S; the heartbeat is
    touched every pass (WDOG.3). (still_open_ids, filled_ids). Unreadable counts as open."""
    from utils.heartbeat import touch as _hb_touch
    left, filled = list(ids), []
    deadline = time.time() + CANCEL_CONFIRM_S
    while left:
        _hb_touch("boot order sweep")
        for oid in list(left):
            try:
                st = _norm_status(sdk_result(account.get_order(session, oid)))
            except Exception:                                  # noqa: BLE001
                continue
            if st in _DEAD_N:
                left.remove(oid)
            elif st == "FILLED":
                left.remove(oid)
                filled.append(oid)
        if not left or time.time() >= deadline:
            break
        time.sleep(_POLL_S)
    return left, filled


def _boot_result(ok: bool, n: int, why: str) -> tuple:
    was = _BOOT["state"]
    _BOOT["state"], _BOOT["why"] = ("clean" if ok else "blocked"), why
    inst = os.environ.get("OT_INSTRUMENT", "")
    if ok:
        logger.info("[guard] boot sweep [%s] clean: %s", inst, why)
        if n:
            _page(f"⚠️ ORDER GUARD [{inst}] — restart found {n} leftover working order(s) and "
                  f"cancelled them before posting anything. If one had part-filled, reconcile "
                  f"adopts the position.")
        elif was == "blocked":
            _page(f"✅ ORDER GUARD [{inst}] — working-order sweep now clean; entries resume.")
        _BOOT["paged"] = False
    else:
        logger.error("[guard] boot sweep [%s] BLOCKED: %s — no live entry posts until a sweep "
                     "comes back clean", inst, why)
        if not _BOOT["paged"]:
            _BOOT["paged"] = True
            _page(f"🔴 ORDER GUARD [{inst}] — restart could not clear its working orders ({why}). "
                  f"NO ENTRIES until it can; exits are unaffected. Check the order book.")
    return ok, n, why


def boot_sweep() -> tuple:
    """LIVE boot hook (main._recover_open_position). Never raises."""
    try:
        from data.tasty_client import get_session, get_account
        session, account = get_session(), get_account()
    except Exception as exc:                                   # noqa: BLE001
        return _boot_result(False, 0, f"no broker session ({type(exc).__name__})")
    return sweep_working(session, account)


def clear_to_post(key: str, session, account) -> tuple:
    """(ok, why). ok=False means DO NOT POST for this intent this tick."""
    if _BOOT["state"] != "clean":                               # r495 B4
        ok, _n, why = sweep_working(session, account)
        if not ok:
            return False, f"boot sweep: {why}"
    s = _SUSPECT.get(key)
    if not s:
        return True, ""
    try:
        placed = sdk_result(account.get_order(session, s["order_id"]))
        status = _status_name(placed)
    except Exception as exc:                                   # noqa: BLE001
        return False, f"suspect order {s['order_id']} unreadable ({type(exc).__name__})"
    if status in _DEAD:
        _SUSPECT.pop(key, None)
        logger.info("[guard] suspect order %s is %s — intent cleared", s["order_id"], status)
        return True, f"suspect {s['order_id']} {status}"
    if status == "FILLED":
        if not s["paged_fill"]:
            s["paged_fill"] = True
            _page(f"🔴 ORDER GUARD — {s['what']}: order {s['order_id']} FILLED after an error "
                  f"and is NOT in the DB. No new entry on this intent; reconcile adopts it.")
        return False, f"suspect {s['order_id']} FILLED but unrecorded"
    return False, f"suspect {s['order_id']} still {status or 'unknown'}"


def reset(boot_clean: bool = True) -> None:
    """Tests only. boot_clean=True marks the r495 sweep done (the B2 gates predate it);
    False leaves it pending, as a fresh process is."""
    _SUSPECT.clear()
    _BOOT.update(state="clean" if boot_clean else None, why="", paged=False)
