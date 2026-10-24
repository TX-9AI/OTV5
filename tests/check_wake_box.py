#!/usr/bin/env python3
"""tests/check_wake_box.py — v1.0
v1.0  2026-10-04  OTV4TEST r233 (WAKE.1) — THE WAKE TOOL STARTS SPX-TEST AND NOTHING ELSE.

  The operator, 2026-10-04: "I do want to assign you permission to wake SPX-TEST.
  This is for diagnostic checks or git actions." Every case drives the REAL
  tools/wake_box.main() with a FAKE ec2 client injected through make_client, in a
  fresh interpreter, and reads the fake's call record - never a real AWS call.
  W1  stopped  -> exactly ONE StartInstances with the matched id, then waits to running
  W2  running  -> no StartInstances
  W3  stopping -> refused (2), no StartInstances
  W4  a name off the allow-list -> refused (2) with NO AWS call at all
  W5  two instances tagged -> refused (2), both ids named, no start
  W6  the match is THIS instance -> refused (2), no start
  W7  UnauthorizedOperation -> exit 3, names the inline policy
  W8  --status never calls StartInstances, exit 0
  W9  one log line per run
Run: python3 tests/check_wake_box.py
"""
import json, os, subprocess, sys, tempfile
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


_DRIVER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
spec = json.loads(sys.argv[2])
import tools.wake_box as wb
calls = []

class Err(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}

class Fake:
    def __init__(self):
        self.n = 0
    def describe_instances(self, Filters):
        calls.append(["describe", Filters[0]["Values"][0]])
        if spec.get("err") == "describe":
            raise Err("UnauthorizedOperation")
        states = spec["states"]
        st = states[min(self.n, len(states) - 1)]
        self.n += 1
        insts = [{"InstanceId": i, "State": {"Name": st}, "PrivateIpAddress": "10.0.0.9",
                  "LaunchTime": "2026-10-04T12:05:00Z"} for i in spec["ids"]]
        return {"Reservations": [{"Instances": insts}]}
    def stop_instances(self, **kw):
        calls.append(["stop", kw])
        return {}
    def __getattr__(self, name):          # any other API the tool reaches for is recorded
        def other(*a, **kw):
            calls.append(["OTHER", name])
            return {}
        return other
    def start_instances(self, InstanceIds):
        calls.append(["start", InstanceIds])
        if spec.get("err") == "start":
            raise Err("UnauthorizedOperation")
        return {}

wb.make_client = lambda: Fake()
wb.self_instance_id = lambda: spec.get("self")
wb.POLL_S = 0
if spec.get("now"):
    from datetime import datetime
    wb.now_et = lambda: datetime.fromisoformat(spec["now"]).replace(tzinfo=wb.ET)
rc = wb.main(spec["argv"])
print("@@" + json.dumps({"rc": rc, "calls": calls}))
'''


def run(argv, ids=("i-spx",), states=("stopped", "pending", "running"), err=None, self_id="i-qqq", now=None):
    d = tempfile.mkdtemp(prefix="check_wake_box_")
    log = os.path.join(d, "wake_box.log")
    env = dict(os.environ, OT_WAKE_LOG=log)
    spec = {"argv": argv, "ids": list(ids), "states": list(states), "err": err, "self": self_id, "now": now}
    p = subprocess.run([sys.executable, "-c", _DRIVER, _root, json.dumps(spec)],
                       capture_output=True, text=True, env=env, timeout=60)
    out = p.stdout
    tag = [l for l in out.splitlines() if l.startswith("@@")]
    res = json.loads(tag[-1][2:]) if tag else {"rc": None, "calls": [], "err": p.stderr[-300:]}
    res["out"] = out
    res["log"] = open(log).read().splitlines() if os.path.exists(log) else []
    return res


def stops(r):
    return [c for c in r["calls"] if c[0] == "stop"]


def starts(r):
    return [c for c in r["calls"] if c[0] == "start"]


def main():
    try:
        r = run(["SPX-TEST"])
        check("W1 stopped -> one StartInstances with the matched id, then running",
              r["rc"] == 0 and starts(r) == [["start", ["i-spx"]]] and "running" in r["out"], r)
        r = run(["SPX-TEST"], states=("running",))
        check("W2 running -> no StartInstances", r["rc"] == 0 and not starts(r), r)
        r = run(["SPX-TEST"], states=("stopping",))
        check("W3 stopping -> refused, no StartInstances", r["rc"] == 2 and not starts(r), r)
        r = run(["QQQ-TEST"])
        check("W4 a name off the allow-list -> refused with NO AWS call",
              r["rc"] == 2 and r["calls"] == [], r)
        r = run(["SPX-TEST"], ids=("i-a", "i-b"))
        check("W5 two tagged -> refused, both ids named, no start",
              r["rc"] == 2 and not starts(r) and "i-a" in r["out"] and "i-b" in r["out"], r)
        r = run(["SPX-TEST"], ids=("i-qqq",))
        check("W6 the match is THIS instance -> refused, no start",
              r["rc"] == 2 and not starts(r), r)
        r1 = run(["SPX-TEST"], err="describe")
        r2 = run(["SPX-TEST"], err="start")
        check("W7 UnauthorizedOperation -> exit 3, names the inline policy",
              r1["rc"] == 3 and r2["rc"] == 3 and "qqq-test-wakes-spx-test" in r1["out"]
              and "qqq-test-wakes-spx-test" in r2["out"], (r1, r2))
        r = run(["SPX-TEST", "--status"])
        check("W8 --status never starts, exit 0", r["rc"] == 0 and not starts(r)
              and "state=stopped" in r["out"], r)
        rs = [run(["SPX-TEST"]), run(["NOPE"]), run(["SPX-TEST", "--status"])]
        check("W9 one log line per run", all(len(x["log"]) == 1 for x in rs),
              [x["log"] for x in rs])
        RUN = ("running", "stopping", "stopped")
        r = run(["SPX-TEST", "--stop"], states=RUN, now="2026-10-05T18:30:00")
        check("W10 stop a running box outside session hours -> ONE StopInstances, no Force/Hibernate, waits to stopped",
              r["rc"] == 0 and stops(r) == [["stop", {"InstanceIds": ["i-spx"]}]] and "stopped" in r["out"]
              and not starts(r) and any("stop" in l and "stopped i-spx" in l for l in r["log"]), r)
        r = run(["SPX-TEST", "--stop"], states=RUN, now="2026-10-05T10:00:00")
        check("W11 stop at 10:00 ET on a Monday WITHOUT --during-session -> refused, NO AWS call",
              r["rc"] == 2 and r["calls"] == [] and "--during-session" in r["out"], r)
        r = run(["SPX-TEST", "--stop", "--during-session"], states=RUN, now="2026-10-05T10:00:00")
        check("W12 the same with --during-session -> stops", r["rc"] == 0 and len(stops(r)) == 1, r)
        r = run(["SPX-TEST", "--stop"], states=RUN, now="2026-10-03T10:00:00")
        check("W13 stop on a Saturday at 10:00 ET -> allowed", r["rc"] == 0 and len(stops(r)) == 1, r)
        r = run(["SPX-TEST", "--stop"], states=("stopped",), now="2026-10-05T18:30:00")
        r2 = run(["SPX-TEST", "--stop"], states=("pending",), now="2026-10-05T18:30:00")
        check("W14 already stopped -> no call; pending -> refused, no call",
              r["rc"] == 0 and not stops(r) and r2["rc"] == 2 and not stops(r2), (r, r2))
        every = [run(["SPX-TEST"]), run(["SPX-TEST", "--stop"], states=RUN, now="2026-10-05T18:30:00"),
                 run(["SPX-TEST", "--stop"], states=("stopping", "stopped"), now="2026-10-05T18:30:00"),
                 run(["SPX-TEST", "--status"])]
        used = {c[0] for x in every for c in x["calls"]}
        check("W15 the tool only ever calls describe / start / stop - nothing else (no terminate, no reboot)",
              used <= {"describe", "start", "stop"} and not any(
                  api in open(os.path.join(_root, "tools", "wake_box.py")).read()
                  for api in ("terminate_instances", "reboot_instances", "modify_instance", "Force=", "Hibernate=")),
              used)
    except Exception as exc:  # noqa: BLE001
        check("W0 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}"); return 1
    print("\nGREEN — the wake tool starts and (guarded) stops SPX-TEST only, and says what it did"); return 0


if __name__ == "__main__":
    sys.exit(main())
