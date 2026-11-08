#!/usr/bin/env python3
"""
tools/shadow_rule_status.py  v5.0
v5.0  2026-11-08  OTV5 r90 (SHADOW.1) - IS EACH LOG-ONLY RULE REALLY LOGGING? The operator, 2026-11-08: "once we start
      trading on Monday I want immediate feedback that it's really logging" (the TCS shadow wrote nothing for a week).
      ON A BOX (default): reads the derived store and bot.log READ-ONLY and prints, since today's 09:30 ET, per rule
      (HUNT_OR_EM, PARK_SMA50): the shadow rows, their verdict mix, the [shadow-rule] log lines, and the DECISIONS
      the rule had to cover (Hunt: plan_tick rows verdict TAKE / LOG-ONLY; PARK: the ticks that reached a direction,
      i.e. wrote a "gap" check). A rule with decisions to cover and FEWER shadow rows than decisions is RED - so a
      silent rule is caught on its first decision, not a week later. One JSON line (SHADOW_STATUS {...}) closes it.
      ON CONTROL (--fleet): ships this file to every running box through dtp fleet.py (read-only), prints the table,
      exits 1 on any RED, 0 otherwise. Stdlib only (runs under any python3).
Run:  python3 tools/shadow_rule_status.py            (on a box)
      python3 tools/shadow_rule_status.py --fleet    (on control)
      --since HH:MM  (ET, default 09:30)   --day YYYY-MM-DD (default today ET)
"""
import base64
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

RULES = {"HUNT_OR_EM": "shadow_hunt_or_em", "PARK_SMA50": "shadow_park_sma50"}


def _et():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/New_York")
    except Exception:                                           # noqa: BLE001
        return None


def _arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def _since_epoch(day: str, hm: str) -> float:
    z = _et()
    y, m, d = (int(x) for x in day.split("-"))
    h, mi = (int(x) for x in hm.split(":"))
    return datetime(y, m, d, h, mi, tzinfo=z).timestamp()


def _derived_path() -> str:
    p = os.environ.get("OT_DERIVED_DB", "").strip()
    if p:
        return p
    for c in (os.path.expanduser("~/options-trader/data/derived_store.db"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "derived_store.db")):
        if os.path.exists(c):
            return c
    return os.path.expanduser("~/options-trader/data/derived_store.db")


def _log_path() -> str:
    return os.environ.get("OT_LOG_FILE", "").strip() or os.path.expanduser("~/options-trader/bot.log")


def box_status(day: str, since_hm: str, derived: str, logf: str) -> dict:
    t0 = _since_epoch(day, since_hm)
    out = {"symbol": "", "day": day, "since": since_hm, "rules": {}, "errors": []}
    rows, decisions = {r: [] for r in RULES}, {r: 0 for r in RULES}
    try:
        c = sqlite3.connect(f"file:{derived}?mode=ro", uri=True, timeout=5.0)
        try:
            for rule, name in RULES.items():
                rows[rule] = [r[0] or "" for r in c.execute(
                    "SELECT note FROM plan_check WHERE check_name=? AND ts_epoch>=?", (name, t0))]
            decisions["HUNT_OR_EM"] = c.execute(
                "SELECT COUNT(*) FROM plan_tick WHERE strategy='LiquidityHunt' AND verdict IN ('TAKE','LOG-ONLY') "
                "AND ts_epoch>=?", (t0,)).fetchone()[0]
            decisions["PARK_SMA50"] = c.execute(
                "SELECT COUNT(*) FROM plan_check WHERE strategy='PARK' AND check_name='gap' AND ts_epoch>=?",
                (t0,)).fetchone()[0]
            s = c.execute("SELECT symbol FROM plan_tick WHERE ts_epoch>=? LIMIT 1", (t0,)).fetchone()
            out["symbol"] = s[0] if s else ""
        finally:
            c.close()
    except Exception as exc:                                    # noqa: BLE001
        out["errors"].append(f"derived store unreadable: {type(exc).__name__}: {exc}")
    logs = {r: 0 for r in RULES}
    try:
        lt = datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S")     # bot.log stamps the box's local time
        with open(logf, errors="replace") as fh:
            for line in fh:
                if "[shadow-rule]" not in line or line[:19] < lt:
                    continue
                for r in RULES:
                    if f"[shadow-rule] {r} " in line:
                        logs[r] += 1
    except Exception as exc:                                    # noqa: BLE001
        out["errors"].append(f"bot.log unreadable: {type(exc).__name__}")
    red = bool(out["errors"])
    for r in RULES:
        mix = {}
        for note in rows[r]:
            v = (note.split() or ["?"])[0]
            mix[v] = mix.get(v, 0) + 1
        st = "RED" if (decisions[r] > 0 and len(rows[r]) < decisions[r]) else ("GREEN" if rows[r] else "IDLE")
        if decisions[r] > 0 and logs[r] == 0:
            st = "RED"
        red = red or st == "RED"
        out["rules"][r] = {"decisions": decisions[r], "rows": len(rows[r]), "log_lines": logs[r], "mix": mix,
                           "status": st}
    out["status"] = "RED" if red else "GREEN"
    return out


def _print_box(s: dict) -> None:
    print(f"{s['symbol'] or '?':6s} {s['day']} since {s['since']} ET  -> {s['status']}")
    for r, v in s["rules"].items():
        mix = " ".join(f"{k}={n}" for k, n in sorted(v["mix"].items())) or "-"
        print(f"   {r:11s} {v['status']:5s} decisions {v['decisions']:4d}  rows {v['rows']:4d}  log {v['log_lines']:4d}  {mix}")
    for e in s["errors"]:
        print("   ERROR", e)


def fleet(day: str, since_hm: str) -> int:
    me = open(os.path.abspath(__file__), "rb").read()
    b64 = base64.b64encode(me).decode()
    dtp = os.path.expanduser("~/day_trader_pro")
    py = os.path.join(dtp, "venv", "bin", "python")
    cmd = f"echo {b64} | base64 -d > /tmp/srs.py && python3 /tmp/srs.py --day {day} --since {since_hm}; rm -f /tmp/srs.py"
    try:
        p = subprocess.run([py if os.path.exists(py) else "python3", os.path.join(dtp, "fleet.py"), "run", cmd],
                           cwd=dtp, capture_output=True, text=True, timeout=600)
    except Exception as exc:                                    # noqa: BLE001
        print(f"fleet run failed: {exc}")
        return 2
    boxes = []
    for line in (p.stdout or "").splitlines():
        if line.startswith("SHADOW_STATUS "):
            try:
                boxes.append(json.loads(line[len("SHADOW_STATUS "):]))
            except ValueError:
                pass
    if not boxes:
        print("no box answered (is the fleet awake?)")
        print((p.stdout or "")[-800:])
        return 2
    for s in sorted(boxes, key=lambda x: x.get("symbol", "")):
        _print_box(s)
    reds = [s.get("symbol", "?") for s in boxes if s.get("status") == "RED"]
    tot = {r: sum(s["rules"][r]["rows"] for s in boxes) for r in RULES}
    print(f"FLEET {len(boxes)} box(es): " + ", ".join(f"{r} rows {n}" for r, n in tot.items())
          + (f"  RED: {', '.join(reds)}" if reds else "  all GREEN/IDLE"))
    return 1 if reds else 0


def main() -> int:
    z = _et()
    day = _arg("--day") or datetime.now(z).strftime("%Y-%m-%d")
    since = _arg("--since", "09:30")
    if "--fleet" in sys.argv:
        return fleet(day, since)
    s = box_status(day, since, _arg("--derived") or _derived_path(), _arg("--log") or _log_path())
    _print_box(s)
    print("SHADOW_STATUS " + json.dumps(s, sort_keys=True))
    return 1 if s["status"] == "RED" else 0


if __name__ == "__main__":
    sys.exit(main())
