"""
execution/order_guard.py  v5.3
v5.3  2026-11-16  OTV5 r127 (LOP.1, FA.1; the cold audit 2026-11-15, critical) — A place_order THAT RAISES NO LONGER LETS THE
      SAME INTENT POST AGAIN BESIDE A LIVE ORDER. after_failure covers an error AFTER place_order returned; an error FROM
      it (the reply lost, run_async's 30 s TimeoutError while the coroutine completes, a reset mid-read) left no order id,
      no suspect and a clean boot state, so the next tick posted the next rung while the first could be live: two
      contracts at the broker, one in the DB. NEW after_lost_post(key, symbols, session, account, what): the intent
      becomes a LOST suspect (no order id) and is resolved at once and on every clear_to_post from the broker's own book
      (get_live_orders): any OPENING order on the intent's legs received since LOST_SLACK_S before the failed post is
      the candidate. A working candidate is CANCELLED and blocks until it reads dead; a FILLED one (or a dead one with
      leg fills) blocks the intent and pages once (unrecorded, nothing is posted beside it); an unreadable book blocks;
      with no candidate the intent clears only after LOST_GRACE_S, so an order still in flight cannot slip past.
      Live only: paper never places, so it never registers one. Gate tests/check_lost_post.py on the shared
      misbehaving-broker fixture tests/broker_harness.py.
v5.2  2026-11-14  OTV5 r118 (HYG §5.4, HYG.23) — _kept_order_ids no longer reads the standing-offer store: execution/resting_orders
      is deleted (r76 removed its only writer, the ORB standing offer, so the read always returned nothing). It keeps
      every open row's live_exit_state order ids, as before. No behaviour change.
v5.1  2026-11-14  OTV5 r112 (AM.4) — THE SUSPECT-ORDER PAGE NO LONGER SWALLOWS ITS OWN FAILURE. _page() was
      try: send except: pass, so when the alert manager raised, the one page that says "a live order may be working"
      vanished without a line. A failure now logs ERROR with the page's text and spools it (notifications.
      telegram_sender.spool_text, AM.5), so the next start sends it. The operator, 2026-11-14: "Let's fix the top 10
      today" (amnesty bucket AM.4). Gate tests/check_telegram_queue.py v5.2 T16.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
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
    """Never raises. r112 (AM.4): a failed page is logged at ERROR and spooled for the next start, never silent."""
    try:
        from notifications.alert_manager import get_alert_manager
        get_alert_manager()._send(text)
    except Exception as exc:                                   # noqa: BLE001
        logger.error("[guard] PAGE FAILED (%s: %s) - spooled for the next start: %s", type(exc).__name__, exc, text)
        try:
            from notifications.telegram_sender import spool_text
            spool_text(text, why=f"order_guard page failed: {type(exc).__name__}")
        except Exception as exc2:                              # noqa: BLE001
            logger.error("[guard] spool of the failed page FAILED too (%s): %s", exc2, text)


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


# r127 (LOP.1) — a post whose place_order RAISED. The broker may hold the order; the reply never said.
LOST_GRACE_S = 10.0     # with no candidate in the book, the intent stays blocked this long (an order still in flight)
LOST_SLACK_S = 60.0     # a candidate was received no earlier than this before the failed post (clock skew)


def after_lost_post(key: str, symbols, session, account, what: str, exc=None) -> None:
    """place_order RAISED, so the order may be live at the broker with no id here. Remember the intent as a
    LOST suspect and try to resolve it now (cancel what the book shows). Never raises."""
    syms = sorted({str(x).strip() for x in (symbols or []) if str(x or "").strip()})
    _SUSPECT[key] = {"order_id": "", "lost": True, "symbols": syms, "ts": time.time(), "what": what,
                     "paged_fill": False, "paged_working": False, "ids": []}
    logger.error("[guard] %s: place_order RAISED (%s) - the order may be live at the broker; this intent "
                 "posts nothing until the broker's book shows no working or filled order on %s",
                 what, f"{type(exc).__name__}: {exc}" if exc is not None else "no detail", ", ".join(syms))
    if account is None:
        return
    try:
        _resolve_lost(key, _SUSPECT[key], session, account)
    except Exception as e:                                     # noqa: BLE001
        logger.warning("[guard] %s: book read after the failed post failed (%s); clear_to_post retries",
                       what, e)


def _opened_ts(o):
    for name in ("received_at", "in_flight_at", "live_at"):
        v = getattr(o, name, None)
        if v is not None:
            try:
                return float(v.timestamp())
            except Exception:                                  # noqa: BLE001
                continue
    return None


def _is_lost_candidate(o, s: dict) -> bool:
    legs = getattr(o, "legs", None) or []
    if not legs:
        return False
    if not any(str(getattr(lg, "symbol", "") or "").strip() in s["symbols"] for lg in legs):
        return False
    for lg in legs:                                            # opening orders only: never a close
        a = getattr(lg, "action", "")
        a = str(getattr(a, "value", None) or getattr(a, "name", None) or a).upper().replace(" ", "_")
        if "OPEN" not in a:
            return False
    t = _opened_ts(o)
    return t is None or t >= s["ts"] - LOST_SLACK_S          # no timestamp -> a candidate (fail closed)


def _has_fills(o) -> bool:
    for lg in (getattr(o, "legs", None) or []):
        for f in (getattr(lg, "fills", None) or []):
            try:
                if float(getattr(f, "quantity", 0) or 0) > 0:
                    return True
            except Exception:                                  # noqa: BLE001
                return True
    return False


def _resolve_lost(key: str, s: dict, session, account) -> tuple:
    """(ok, why) for a LOST suspect, read from the broker's book. Raises when the book is unreadable."""
    orders = sdk_result(account.get_live_orders(session)) or []
    filled, working, pending = [], [], []
    for o in orders:
        if not _is_lost_candidate(o, s):
            continue
        oid = str(getattr(o, "id", "") or "?")
        if oid not in s["ids"]:
            s["ids"].append(oid)
        st = _norm_status(o)
        if st == "FILLED" or (st in _DEAD_N and _has_fills(o)):
            filled.append(oid)
        elif st in _WORKING:
            working.append(oid)
        elif st not in _DEAD_N:
            pending.append(f"{oid} {st or 'unknown'}")           # cancel requested, or a status not known here
    for oid in working:
        try:
            sdk_result(account.delete_order(session, oid))
            logger.warning("[guard] %s: cancelled order %s left working by a failed post", s["what"], oid)
        except Exception as exc:                               # noqa: BLE001
            logger.error("[guard] %s: cancel of %s (left by a failed post) FAILED: %s", s["what"], oid, exc)
    if filled:
        if not s["paged_fill"]:
            s["paged_fill"] = True
            _page(f"🔴 ORDER GUARD — {s['what']}: place_order raised but the broker FILLED order(s) "
                  f"{', '.join(filled)} on {', '.join(s['symbols'])}. NOT in the DB; no new entry on this intent.")
        return False, f"lost post: {', '.join(filled)} FILLED but unrecorded"
    if working or pending:
        if working and not s["paged_working"]:
            s["paged_working"] = True
            _page(f"⚠️ ORDER GUARD — {s['what']}: place_order raised but order(s) {', '.join(working)} reached "
                  f"the broker; cancel requested, no re-post until they read dead.")
        return False, f"lost post: {', '.join(working + pending)} still working"
    age = time.time() - s["ts"]
    if age < LOST_GRACE_S:
        return False, f"lost post: no order in the book yet, waiting {LOST_GRACE_S - age:.0f}s more"
    _SUSPECT.pop(key, None)
    logger.info("[guard] %s: the failed post left no live or filled order (%s) - intent cleared",
                s["what"], ", ".join(s["ids"]) or "none seen")
    return True, "lost post: nothing at the broker"


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
    """Order ids this box still tracks across a restart: every open row's live_exit_state order
    ids (B3). r118 (HYG.23): the standing-offer store it also read is deleted (no writer since
    r76). Raises when the rows are unreadable — the caller then cancels NOTHING and blocks entries."""
    keep = set()
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
    if s.get("lost"):                                           # r127 (LOP.1)
        try:
            return _resolve_lost(key, s, session, account)
        except Exception as exc:                               # noqa: BLE001
            return False, f"lost post: broker book unreadable ({type(exc).__name__})"
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
