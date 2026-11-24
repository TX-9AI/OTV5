#!/usr/bin/env python3
"""
tests/check_probe_dryrun.py  v5.1
v5.1  2026-11-24  OTV5 r157 (PRB.2 upgrade) — THE PROBE DRY-RUNS THE BOT'S OWN ORDERS, ON AN EXPIRY STILL TRADING, AND
      ITS GUARDS HOLD (tools/probe_order_dryrun v5.2; the operator, 2026-11-24: "Go ahead"). D1-D5 unchanged; new,
      driven, no network:
  D6  layer 2: install_guards() on a stand-in Account class - place_order with dry_run False or omitted RAISES
      LiveSubmitRefused before the stand-in is reached; dry_run True reaches it with True; replace_order /
      place_complex_order / delete_order raise; a second install does not double-wrap
  D7  layer 1: a DryRunAccount over the guarded stand-in - the bot-style call place_order(s, o, dry_run=<live>) reaches
      the stand-in as dry_run=True and records what the caller asked; any other method (get_balances) raises
  D8  layer 3: guard_session() - an order POST that is not /dry-run, a complex-order POST, any order PUT / DELETE
      raise; the /dry-run POST and a non-order POST pass
  D9  end to end: the REAL ExitEngine._submit_live_close (which asks for a LIVE order) driven by run_exits() over the
      DryRunAccount and the guarded stand-in: every close reached the stand-in as a dry run, one per scenario, the
      caller's ask recorded as the live one, no page sent
  D10 expiry, fixture clock: before 16:15 today's expiry; at 16:20 the NEXT LISTED one (11-25 -> 11-27 across the
      unlisted Thanksgiving 11-26); no expiry today -> the nearest listed (fetch_chain's fallback); an AM-only date
      (SPX) is never picked; only today's contracts still trading are returned
  D11 the same choice as the REAL OptionsChainFetcher.fetch_chain on the same fixture (stubbed session, structure and
      store): before the stop = fetch_chain(expiry=None); after it = fetch_chain(expiry=tomorrow)
  D12 entry: on a fixture quote (QQQ 3.40 / 3.50, the venue rule 0.01 cached) entry_orders() builds 3.42, 3.43, 3.44,
      3.45 (DAY LIMIT Buy to Open x1, debit) and each order is byte-identical (model_dump_json) to the order the REAL
      EntryEngine._place_single_leg posts on the same quote, rung for rung
  D13 exits: run_exits() posts, on the same quote, the stop at the mark 3.45 (passes 1-2), at the bid 3.40 (pass 3),
      MARKET (pass 4), PARK's walk 3.48, the EOD ladder 3.48 at 15:50 and the EOD cross MARKET at 15:55 (12:50 / 12:55
      on the 11-27 half day), all Sell to Close x1 DAY - each byte-identical to what a direct call of the REAL
      _submit_live_close posts with the same record and clock
  D14 the verdict: a Sell to Close whose only objection names the position is EXPECTED; one with another objection,
      and a Buy to Open with the same text, are REJECTED; no objection is ACCEPTED; buying power / PDT / approval
      warnings are tagged; _scrub masks the account string
  D15 no production module imports the probe (main.py, config.py, data/, execution/, strategy/, risk/, utils/,
      database/, notifications/, warehouse/, derived/ - no import of it and no mention of its name)
Born red on r156 (e25c028) at D6-D14 (no guards, no expiry rule, no builders); D1-D5 and D15 pass there. Mutants (each
red, measured): the layer-2 guard passes dry_run through instead of raising (D2, D6); DryRunAccount forwards the
caller's dry_run to the real place_order (D1, D7, D9, D13); the session guard allows any POST (D8); pick_expiry ignores
stops_trading_at (D10, D11); the entry order drops the debit sign (D12); run_exits' clock not pinned (D13).
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-04  OTV4TEST r239 (PRB.2) — THE ORDER PROBE CAN ONLY EVER DRY-RUN.

  The operator, 2026-10-04: "Yes, to the dry run if you can do it without actually spending money."
  tools/probe_order_dryrun.py calls the broker's place_order. This gate proves, by reading its AST, that it
  cannot place a real order:
  D1  exactly one place_order call exists, inside _dry(), with the keyword dry_run set to the literal True
  D2  no `dry_run=False`, no `dry_run=` bound to anything but the constant True, anywhere in the file
  D3  every NewOrder the probe builds reaches the broker only through _dry() (no other attribute call on
      `account` that could submit: place_order / replace_order / place_complex_order)
  D4  the probe is on run_with_bot_env's PROBES list (so it runs only committed and unedited)
  D5  it prints no account number and no balance field (current_buying_power / new_buying_power / net_liq)
No network. Run: python3 tests/check_probe_dryrun.py   (D6-D14 need the venv's tastytrade)
"""
import ast, os, sys, tempfile
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def static_checks():
    p = os.path.join(_root, "tools", "probe_order_dryrun.py")
    try:
        src = open(p).read()
        tree = ast.parse(src)
    except Exception as exc:  # noqa: BLE001
        check("D0 the probe exists and parses", False, f"{type(exc).__name__}: {exc}")
        return False
    calls, owners = [], {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                owners.setdefault(id(c), fn.name)
    for c in ast.walk(tree):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in (
                "place_order", "replace_order", "place_complex_order"):
            calls.append(c)
    def _dry_true(c):
        kw = [k for k in c.keywords if k.arg == "dry_run"]
        return len(kw) == 1 and isinstance(kw[0].value, ast.Constant) and kw[0].value.value is True
    check("D1 exactly one place_order call, inside _dry(), with dry_run=True (literal)",
          len(calls) == 1 and calls[0].func.attr == "place_order" and owners.get(id(calls[0])) == "_dry"
          and _dry_true(calls[0]), [(c.func.attr, owners.get(id(c)), _dry_true(c)) for c in calls])
    bad_kw = [k for c in ast.walk(tree) if isinstance(c, ast.Call) for k in c.keywords
              if k.arg == "dry_run" and not (isinstance(k.value, ast.Constant) and k.value.value is True)]
    check("D2 no dry_run bound to anything but the constant True", not bad_kw and "dry_run=False" not in src,
          len(bad_kw))
    check("D3 no other submitting call (replace_order / place_complex_order)",
          all(c.func.attr == "place_order" for c in calls))
    w = open(os.path.join(_root, "tools", "run_with_bot_env.py")).read()
    check("D4 the probe is on run_with_bot_env's PROBES list",
          '"probe_order_dryrun.py": "tools/probe_order_dryrun.py"' in w)
    prints = [ast.get_source_segment(src, c) or "" for c in ast.walk(tree)
              if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "print"]
    leak = [s for s in prints if any(k in s for k in ("current_buying_power", "new_buying_power",
                                                       "net_liq", "account_number", "get_tt_account_number"))]
    check("D5 prints no account number and no balance", not leak, leak[:2])
    return True


def production_import_check():
    """D15 - no module the bot runs imports or names the probe."""
    hits = []
    tops = ("main.py", "config.py", "data", "execution", "strategy", "risk", "utils", "database",
            "notifications", "warehouse", "derived")
    for top in tops:
        base = os.path.join(_root, top)
        files = [base] if base.endswith(".py") else [
            os.path.join(d, f) for d, _s, fs in os.walk(base) for f in fs if f.endswith(".py")]
        for f in files:
            if not os.path.isfile(f):
                continue
            src = open(f, errors="replace").read()
            if "probe_order_dryrun" in src:
                hits.append(os.path.relpath(f, _root))
    check("D15 no production module imports or names the probe", not hits, hits[:5])


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# D6-D14 - driven. Scratch stores; QQQ.
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════

def driven_checks():
    import asyncio
    import json
    from datetime import date, datetime, timedelta
    from types import SimpleNamespace
    _td = tempfile.mkdtemp(prefix="check_probe_dryrun.")
    for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
                   ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"),
                   ("OT_PLAN_STATES_FILE", "ps.json"), ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
        os.environ.setdefault(_k, os.path.join(_td, _v))
    os.environ["OT_INSTRUMENT"] = "QQQ"
    sys.path.insert(0, _root)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("probe_order_dryrun",
                                                      os.path.join(_root, "tools", "probe_order_dryrun.py"))
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
        from utils.time_utils import ET
        import utils.time_utils as TU
        from execution import ladder_registry as LR
        from execution import tick_size as TS
        import execution.exit_engine as XE
        from execution import entry_engine as EE
        from data import options_chain as OC
        import data.tasty_client as TC
    except SystemExit as exc:
        check("D6 the probe and the bot modules import here", False, f"exit {exc.code} (needs the venv's tastytrade)")
        return
    except Exception as exc:  # noqa: BLE001
        check("D6 the probe and the bot modules import here", False, f"{type(exc).__name__}: {exc}")
        return
    need = [n for n in ("install_guards", "DryRunAccount", "guard_session", "pick_expiry", "entry_orders",
                        "run_exits", "verdict", "_scrub", "LiveSubmitRefused") if not hasattr(P, n)]
    if need:
        for d in ("D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "D14"):
            check(f"{d} the probe carries the v5.2 surface", False, f"missing {need}")
        return
    Refused = P.LiveSubmitRefused
    from tastytrade.order import OrderAction

    def run(coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def dump(o):
        return o.model_dump_json(by_alias=True, exclude_none=True)

    # ── a stand-in Account class: async, records what reached it ─────────────────────────────────────────────
    def stand_in():
        class Stand:
            reached = []

            async def place_order(self, session, order, dry_run=True):
                Stand.reached.append({"order": order, "dry_run": dry_run})
                return SimpleNamespace(errors=None, warnings=None, order=SimpleNamespace(id=None),
                                       buying_power_effect=SimpleNamespace(change_in_buying_power=0, effect="None"),
                                       fee_calculation=SimpleNamespace(total_fees=0))

            async def replace_order(self, *a, **k):
                Stand.reached.append({"replace": True})

            async def place_complex_order(self, *a, **k):
                Stand.reached.append({"complex": True})

            async def delete_order(self, *a, **k):
                Stand.reached.append({"delete": True})
        return Stand

    # D6 ─────────────────────────────────────────────────────────────────────────────────────────────────────
    S = stand_in()
    P.install_guards(S)
    P.install_guards(S)                                               # idempotent
    acct = S()
    res = {}
    for label, kw in (("live", {"dry_run": bool(0)}), ("omitted", {}), ("none", {"dry_run": None})):
        try:
            run(acct.place_order("s", "o", **kw))
            res[label] = "sent"
        except Refused:
            res[label] = "refused"
        except Exception as exc:  # noqa: BLE001
            res[label] = type(exc).__name__
    live_reached = len(S.reached)
    run(acct.place_order("s", "o", dry_run=True))
    other = {}
    for name in ("replace_order", "place_complex_order", "delete_order"):
        try:
            run(getattr(acct, name)("s", 1, "o"))
            other[name] = "ran"
        except Refused:
            other[name] = "refused"
    check("D6 layer 2: Account.place_order raises unless dry_run is True; the other submit / cancel methods raise",
          res == {"live": "refused", "omitted": "refused", "none": "refused"} and live_reached == 0
          and len(S.reached) == 1 and S.reached[0]["dry_run"] is True
          and set(other.values()) == {"refused"},
          f"{res} reached-before-True={live_reached} reached={S.reached} other={other}")

    # D7 ─────────────────────────────────────────────────────────────────────────────────────────────────────
    S2 = stand_in()
    P.install_guards(S2)
    dra = P.DryRunAccount(S2(), "SESSION")
    ok_call = True
    try:
        dra.place_order("BOT-SESSION", "ORDER", dry_run=bool(0))      # what the bot's own submit asks for
    except Exception:  # noqa: BLE001
        ok_call = False
    try:
        dra.get_balances("s")
        bal = "ran"
    except Refused:
        bal = "refused"
    check("D7 layer 1: the bot's live ask reaches the broker as dry_run=True; any other account method raises",
          ok_call and len(S2.reached) == 1 and S2.reached[0]["dry_run"] is True
          and dra.calls and dra.calls[0]["bot_asked"] is False and bal == "refused",
          f"call ok={ok_call} reached={S2.reached} calls={[c.get('bot_asked') for c in dra.calls]} balances={bal}")

    # D8 ─────────────────────────────────────────────────────────────────────────────────────────────────────
    class Sess:
        def __init__(self):
            self.hit = []

        async def _post(self, url, **k):
            self.hit.append(("POST", url))
            return {}

        async def _put(self, url, **k):
            self.hit.append(("PUT", url))
            return {}

        async def _delete(self, url, **k):
            self.hit.append(("DELETE", url))
    s = P.guard_session(Sess())
    out = {}
    for label, fn, url in (("post-live", "_post", "/accounts/A1/orders"),
                           ("post-complex", "_post", "/accounts/A1/complex-orders"),
                           ("put", "_put", "/accounts/A1/orders/7"),
                           ("delete", "_delete", "/accounts/A1/orders/7"),
                           ("post-dry", "_post", "/accounts/A1/orders/dry-run"),
                           ("post-other", "_post", "/oauth/token")):
        try:
            run(getattr(s, fn)(url))
            out[label] = "sent"
        except Refused:
            out[label] = "refused"
    check("D8 layer 3: only a /dry-run order POST leaves the session; order PUT / DELETE and live POSTs raise",
          out == {"post-live": "refused", "post-complex": "refused", "put": "refused", "delete": "refused",
                  "post-dry": "sent", "post-other": "sent"}
          and s.hit == [("POST", "/accounts/A1/orders/dry-run"), ("POST", "/oauth/token")], f"{out} {s.hit}")

    # quote + venue grid for D9 / D12 / D13 ───────────────────────────────────────────────────────────────────
    TS.cache_venue_rule("QQQ", [SimpleNamespace(threshold=None, value=0.01)])
    OCC, BID, ASK = "QQQ   261125C00600000", 3.40, 3.50
    FULL = datetime(2026, 11, 25, 10, 30, tzinfo=ET)
    HALF = datetime(2026, 11, 27, 10, 30, tzinfo=ET)

    # D9 ─────────────────────────────────────────────────────────────────────────────────────────────────────
    S3 = stand_in()
    P.install_guards(S3)
    dra3 = P.DryRunAccount(S3(), "SESSION")
    pages = []
    try:
        rows = P.run_exits(dra3, "SESSION", OCC, BID, ASK, 1, FULL, collect=pages)
        err = ""
    except Exception as exc:  # noqa: BLE001
        rows, err = [], f"{type(exc).__name__}: {exc}"
    n_sc = len(P.exit_scenarios(FULL)) if not err else -1
    asked = [c["bot_asked"] for c in dra3.calls]
    check("D9 end to end: every close the REAL _submit_live_close submitted (asking LIVE) reached the broker as a dry "
          "run, one per scenario, no page sent",
          not err and len(rows) == n_sc and len(S3.reached) == n_sc and n_sc >= 7
          and all(r["dry_run"] is True for r in S3.reached) and asked == [False] * n_sc
          and all(len(r[-1]) == 1 for r in rows),
          f"{err} scenarios={n_sc} rows={len(rows)} reached={len(S3.reached)} asked={asked}")

    # D10 / D11 ──────────────────────────────────────────────────────────────────────────────────────────────
    def opt(d, typ="C", k=600.0, settle="PM", stop=None, root="QQQ"):
        from tastytrade.instruments import OptionType
        stop = stop or datetime(d.year, d.month, d.day, 16, 15, tzinfo=ET)
        sym = f"{root:<6}{d:%y%m%d}{typ}{int(k * 1000):08d}"
        return SimpleNamespace(symbol=sym, option_type=OptionType.CALL if typ == "C" else OptionType.PUT,
                               strike_price=k, streamer_symbol=f".{root}{d:%y%m%d}{typ}{int(k)}",
                               settlement_type=settle, stops_trading_at=stop, root_symbol=root,
                               expiration_date=d)
    D25, D27, D30 = date(2026, 11, 25), date(2026, 11, 27), date(2026, 11, 30)
    chain = {D25: [opt(D25), opt(D25, "P")], D27: [opt(D27), opt(D27, "P")], D30: [opt(D30)]}
    am = {D27: [opt(D27, settle="AM", root="SPX")], D30: [opt(D30, root="SPXW")]}
    mixed_stop = {D25: [opt(D25), opt(D25, k=601.0, stop=datetime(2026, 11, 25, 16, 0, tzinfo=ET))], D27: [opt(D27)]}
    c_before = P.pick_expiry(chain, datetime(2026, 11, 25, 16, 10, tzinfo=ET))
    c_after = P.pick_expiry(chain, datetime(2026, 11, 25, 16, 20, tzinfo=ET))
    c_none = P.pick_expiry(chain, datetime(2026, 11, 26, 10, 0, tzinfo=ET))
    c_am = P.pick_expiry(am, datetime(2026, 11, 27, 10, 0, tzinfo=ET))
    c_mix = P.pick_expiry(mixed_stop, datetime(2026, 11, 25, 16, 5, tzinfo=ET))
    check("D10 expiry on a fixture clock: today before the stop, the NEXT LISTED after it (11-25 16:20 -> 11-27), the "
          "nearest listed with none today, never an AM-only date, only today's still-trading contracts",
          c_before[0] == D25 and c_after[0] == D27 and c_none[0] == D27 and c_am[0] == D30
          and c_mix[0] == D25 and len(c_mix[1]) == 1 and float(c_mix[1][0].strike_price) == 600.0
          and len(c_after[1]) == 2,
          f"before={c_before[0]} after={c_after[0]} none={c_none[0]} am={c_am[0]} mix={c_mix[0]}/{len(c_mix[1])}")

    def fetch_choice(cmap, now, expiry=None, sym="QQQ"):
        f = OC.OptionsChainFetcher()
        seen = []
        f._get_chain_structure = lambda session, symbol: cmap
        f._fetch_greeks_and_quotes = lambda session, syms, expiry="": seen.append(expiry) or ({}, {})
        saved = (OC.get_session, TU.now_et)
        OC.get_session = lambda: object()
        TU.now_et = lambda: now
        try:
            import data.open_interest as _oi
            _soi = _oi.fetch_open_interest
            _oi.fetch_open_interest = lambda *a, **k: {}
        except Exception:  # noqa: BLE001
            _oi = None
        try:
            ch = f.fetch_chain(sym, expiry=expiry)
        finally:
            OC.get_session, TU.now_et = saved
            if _oi is not None:
                _oi.fetch_open_interest = _soi
        got = getattr(ch, "expiry", "") or (seen[0] if seen else "")
        return date.fromisoformat(got) if got else None
    t_before = datetime(2026, 11, 25, 16, 10, tzinfo=ET)
    t_after = datetime(2026, 11, 25, 16, 20, tzinfo=ET)
    f_before = fetch_choice(chain, t_before)
    f_after = fetch_choice(chain, t_after, expiry=(t_after.date() + timedelta(days=1)).isoformat())
    f_none = fetch_choice(chain, datetime(2026, 11, 26, 10, 0, tzinfo=ET))
    f_am = fetch_choice(am, datetime(2026, 11, 27, 10, 0, tzinfo=ET), sym="SPX")
    check("D11 the same expiry as the REAL fetch_chain (before the stop: expiry=None; after it: expiry=tomorrow; "
          "none today; AM-only)",
          (f_before, f_after, f_none, f_am) == (c_before[0], c_after[0], c_none[0], c_am[0]),
          f"fetch_chain={(f_before, f_after, f_none, f_am)} probe={(c_before[0], c_after[0], c_none[0], c_am[0])}")

    # D12 ────────────────────────────────────────────────────────────────────────────────────────────────────
    probe_rungs = P.entry_orders(OCC, BID, ASK, 1, "QQQ")
    posted = []

    class Cap:
        def place_order(self, session, order, dry_run=None):
            posted.append(order)
            return SimpleNamespace(errors=[], order=SimpleNamespace(id="T"))
    saved = {k: getattr(EE, k) for k in ("get_session", "get_account", "sdk_result", "confirm_order_fill")}
    saved_g = (EE._guard.clear_to_post, EE._guard.after_failure, EE._guard.after_lost_post, EE._bp.affordable)
    had_piw = "_page_if_working" in EE.EntryEngine.__dict__
    saved_piw = EE.EntryEngine.__dict__.get("_page_if_working")
    EE.get_session = lambda: object()
    EE.get_account = lambda: Cap()
    EE.sdk_result = lambda r: r
    EE.confirm_order_fill = lambda *a, **k: SimpleNamespace(filled=False, net_price=None, working_order_id=None,
                                                            detail="stub: refused", order_id="T", quantity=0)
    EE._guard.clear_to_post = lambda *a, **k: (True, "")
    EE._guard.after_failure = lambda *a, **k: None
    EE._guard.after_lost_post = lambda *a, **k: None
    EE._bp.affordable = lambda *a, **k: (True, "")
    EE.EntryEngine._page_if_working = staticmethod(lambda *a, **k: None)
    try:
        LR.reset_all()
        live = EE.EntryEngine(paper_trading=False)
        sig = SimpleNamespace(contract=SimpleNamespace(symbol=OCC, bid=BID, ask=ASK),
                              entry_premium=round((BID + ASK) / 2.0, 4), strategy_name="T", setup_type="t")
        for _ in range(len(probe_rungs) + 2):
            live._place_single_leg(sig, 1)
    finally:
        for k, v in saved.items():
            setattr(EE, k, v)
        (EE._guard.clear_to_post, EE._guard.after_failure, EE._guard.after_lost_post, EE._bp.affordable) = saved_g
        if had_piw:
            EE.EntryEngine._page_if_working = saved_piw
        else:
            del EE.EntryEngine._page_if_working
        LR.reset_all()
    walk = []
    for o in posted:                                                  # the real walk up to its first re-offer
        px = -float(o.price)
        if walk and px <= -float(walk[-1].price) + 1e-9:
            break
        walk.append(o)
    prices = [round(r[0], 2) for r in probe_rungs]
    d_probe = [dump(r[2]) for r in probe_rungs]
    d_real = [dump(o) for o in walk]
    shape = [P.describe(r[2]) for r in probe_rungs]
    check("D12 entry: the probe's rungs are 3.42 3.43 3.44 3.45 (DAY LIMIT Buy to Open x1, debit) and byte-identical "
          "to the orders the REAL _place_single_leg posts on the same quote",
          prices == [3.42, 3.43, 3.44, 3.45] and d_probe == d_real
          and all(s["type"] == "Limit" and s["tif"] == "Day" and s["effect"] == "Debit"
                  and s["legs"] == [("Buy to Open", 1, OCC)] for s in shape),
          f"probe={prices} real={[-float(o.price) for o in posted]} same={d_probe == d_real} shape={shape[:1]}")

    # D13 ────────────────────────────────────────────────────────────────────────────────────────────────────
    def direct(now):
        """An independent drive of the REAL _submit_live_close: the same records and clocks, a capture account."""
        got = []

        class CapX:
            def place_order(self, session, order, dry_run=None):
                got.append(order)
                return SimpleNamespace(errors=None, order=SimpleNamespace(id="X"))
        eng = XE.ExitEngine.__new__(XE.ExitEngine)
        eng._live_exit_alerted = set()
        eng._alert_live_exit_once = lambda *a, **k: None
        sv = (XE.get_session, XE.get_account, XE.now_et)
        XE.get_session, XE.get_account = (lambda: "S"), (lambda: CapX())
        per = []
        try:
            for i, (title, strat, reason, n, clock) in enumerate(P.exit_scenarios(now)):
                XE.now_et = (lambda c: (lambda: c))(clock)
                rec = {"trade_id": f"PRB2X{i:02d}{reason[:16]}", "option_symbol": OCC, "symbol": "QQQ",
                       "strategy": strat, "_exit_bid": BID, "_exit_ask": ASK, "_stop_unfilled": n}
                b = len(got)
                eng._submit_live_close(rec, 1, round((BID + ASK) / 2.0, 4), reason=reason)
                eng._exit_walk_done(rec)
                per.append(([dump(o) for o in got[b:]], clock))
        finally:
            XE.get_session, XE.get_account, XE.now_et = sv
        return per

    def probe_side(now):
        S4 = stand_in()
        P.install_guards(S4)
        d4 = P.DryRunAccount(S4(), "SESSION")
        rows4 = P.run_exits(d4, "SESSION", OCC, BID, ASK, 1, now)
        return [([dump(c["order"]) for c in r[-1]], r[3]) for r in rows4], [
            [P.describe(c["order"]) for c in r[-1]] for r in rows4]
    want_px = ["3.45", "3.45", "3.4", "MKT", "3.48", "3.48", "MKT"]
    detail, ok13 = [], True
    for now, lad, crs in ((FULL, (15, 50), (15, 55)), (HALF, (12, 50), (12, 55))):
        try:
            pr, shapes = probe_side(now)
            dr = direct(now)
        except Exception as exc:  # noqa: BLE001
            ok13 = False
            detail.append(f"{now:%m-%d} {type(exc).__name__}: {exc}")
            continue
        px = []
        for sh in shapes:
            if len(sh) != 1:
                px.append(f"n={len(sh)}")
                continue
            s1 = sh[0]
            px.append("MKT" if s1["type"] == "Market" else str(float(s1["price"])).rstrip("0").rstrip("."))
            if s1["tif"] != "Day" or s1["legs"] != [("Sell to Close", 1, OCC)]:
                ok13 = False
                detail.append(f"{now:%m-%d} shape {s1}")
        clocks = [(c.hour, c.minute) for _d, c in pr]
        want_px_s = [p.rstrip("0").rstrip(".") if p != "MKT" else p for p in want_px]
        same = [d for d, _c in pr] == [d for d, _c in dr]
        if px != want_px_s or not same or clocks[-2] != lad or clocks[-1] != crs:
            ok13 = False
        detail.append(f"{now:%m-%d} px={px} same_as_direct={same} eod_clocks={clocks[-2:]}")
    check("D13 exits: mark 3.45 x2, the bid 3.40, MARKET; PARK walk 3.48; EOD ladder 3.48 and the cross MARKET at "
          "15:50 / 15:55 (12:50 / 12:55 on the half day); Sell to Close x1 DAY; byte-identical to a direct "
          "_submit_live_close", ok13, "; ".join(detail))

    # D14 ────────────────────────────────────────────────────────────────────────────────────────────────────
    from tastytrade.order import NewOrder, Leg, OrderType, OrderTimeInForce
    from tastytrade.instruments import InstrumentType

    def o_of(action):
        return NewOrder(time_in_force=OrderTimeInForce.DAY, order_type=OrderType.MARKET,
                        legs=[Leg(instrument_type=InstrumentType.EQUITY_OPTION, symbol=OCC, action=action,
                                  quantity=1)])
    stc, bto = o_of(OrderAction.SELL_TO_CLOSE), o_of(OrderAction.BUY_TO_OPEN)
    e_pos = Exception("invalid_closing_order: No position found to close\n")
    e_two = Exception("invalid_closing_order: No position found to close\ninstruments_stopped_trading: stopped\n")
    v1 = P.verdict({"order": stc, "exc": e_pos})[0]
    v2 = P.verdict({"order": stc, "exc": e_two})[0]
    v3 = P.verdict({"order": bto, "exc": e_pos})[0]
    ok_resp = SimpleNamespace(errors=None, warnings=["insufficient_buying_power: x", "pattern_day_trader: y",
                                                     "option_level_not_approved: z"])
    v4, _r4, w4 = P.verdict({"order": bto, "resp": ok_resp})
    tags = [P._tag(w) for w in w4]
    P._MASK.append("5WZ12345")
    sc = P._scrub("account 5WZ12345 refused")
    P._MASK.remove("5WZ12345")
    check("D14 the verdict: a close refused only for the missing position is EXPECTED; any other objection, or the "
          "same text on a Buy to Open, is REJECTED; warnings tagged; the account string masked",
          (v1, v2, v3, v4) == ("EXPECTED", "REJECTED", "REJECTED", "ACCEPTED")
          and tags == ["[buying power] ", "[PDT] ", "[approval level] "] and "5WZ12345" not in sc,
          f"{(v1, v2, v3, v4)} tags={tags} scrub={sc!r}")


def main():
    print("check_probe_dryrun")
    if not static_checks():
        print("\nRED"); return 1
    production_import_check()
    driven_checks()
    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}"); return 1
    print("\nGREEN — the order probe can only ever dry-run, on the bot's own orders"); return 0


if __name__ == "__main__":
    sys.exit(main())
