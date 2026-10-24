#!/usr/bin/env python3
"""tools/wake_box.py — v1.0
WAKE OR STOP ONE NAMED TEST BOX, AND NOTHING ELSE.

v1.0 (2026-10-04) — OTV4TEST r233 (WAKE.1). The operator, 2026-10-04 ~10:18 ET:
      "I do want to assign you permission to wake SPX-TEST. This is for
      diagnostic checks or git actions." He adds an inline policy
      (qqq-test-wakes-spx-test) to this box's instance role: ec2:StartInstances
      on SPX-TEST's instance ARN only, and ec2:DescribeInstances on *. The
      agent's allow rule names exactly `python3 tools/wake_box.py *`.
      The same day, 10:36 ET: "I want you to be able to stop it too." - the
      policy also grants ec2:StopInstances on that ARN. STOP IS GUARDED: on a
      weekday between 09:25 and 16:10 ET it is REFUSED unless --during-session
      is given, and that flag is used ONLY on the operator's own word in the
      thread (a mid-session stop cuts the bot off with positions open).

🔴 NARROW BY CONSTRUCTION:
  1. ONLY A NAME ON `ALLOWED` below - the ruling covers SPX-TEST and no other
     box. Any other name is refused BEFORE any AWS call.
  2. THE INSTANCE IS FOUND BY ITS EC2 Name TAG, never a hard-coded id: zero or
     more than one match is refused (both ids named), and a match that is THIS
     instance is refused.
  3. START and a GUARDED STOP, nothing else: no reboot, no force-stop, no
     hibernate, no terminate, no modify. Start leaves a running box alone and
     refuses a stopping one; stop leaves a stopped box alone, waits on a
     stopping one, and refuses a pending one (retry when it is running).
  4. NO SILENT ACTION (WORKING_AGREEMENT 38.7): every run appends one line to
     logs/wake_box.log - UTC stored; times printed for the operator are ET.
  5. NO CREDENTIAL IS EVER READ OR PRINTED (38.7): IMDS is asked only for the
     instance id and region, never iam/security-credentials.
Exit codes: 0 done / already there / status; 2 refused (name, match, self,
state, session hours); 3 AWS error (its code printed); 4 timed out waiting.

Usage:
  python3 tools/wake_box.py SPX-TEST --status     # read only: state, id, launch
  python3 tools/wake_box.py SPX-TEST [--wait 120] # start it if stopped
  python3 tools/wake_box.py SPX-TEST --stop       # stop it (refused 09:25-16:10 ET weekdays)
  python3 tools/wake_box.py SPX-TEST --stop --during-session   # ONLY on the operator's word
"""
import argparse
import getpass
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ALLOWED = {"SPX-TEST"}
POLICY = "qqq-test-wakes-spx-test"
ET = ZoneInfo("America/New_York")
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.environ.get("OT_WAKE_LOG") or os.path.join(_root, "logs", "wake_box.log")
POLL_S = float(os.environ.get("OT_WAKE_POLL_S", "5"))
_IMDS = "http://169.254.169.254/latest"


def _imds(path: str) -> str | None:
    """One IMDSv2 read of an allowed, non-secret path. None if unreachable."""
    if "security-credentials" in path:          # 38.7 - never, by construction
        raise ValueError("refused: credential path")
    try:
        tok = urllib.request.urlopen(urllib.request.Request(
            _IMDS + "/api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=2).read().decode()
        return urllib.request.urlopen(urllib.request.Request(
            _IMDS + "/meta-data/" + path,
            headers={"X-aws-ec2-metadata-token": tok}), timeout=2).read().decode()
    except Exception:  # noqa: BLE001
        return None


def self_instance_id() -> str | None:
    return _imds("instance-id")


def region() -> str:
    return (os.environ.get("OT_WAKE_REGION") or _imds("placement/region")
            or os.environ.get("OT_S3_REGION", "us-east-2"))


SESSION_START, SESSION_END = (9, 25), (16, 10)     # ET, Mon-Fri: a stop needs --during-session


def now_et() -> datetime:
    """The clock the session guard reads. Module-level so the checker can inject one."""
    return datetime.now(ET)


def in_session(t: datetime) -> bool:
    return t.weekday() < 5 and SESSION_START <= (t.hour, t.minute) < SESSION_END


def make_client():
    """The ec2 client. A module-level factory so the checker can inject a fake."""
    import boto3
    return boto3.client("ec2", region_name=region())


def _log(target: str, action: str, result: str) -> None:
    line = "%s\t%s\t%s\t%s\t%s\n" % (
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        getpass.getuser(), target, action, result)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as fh:
            fh.write(line)
    except OSError as exc:                      # 0.5 - say so, never silent
        print("wake_box: could NOT write %s: %s" % (LOG, exc), file=sys.stderr)


def _code(exc) -> str:
    try:
        return exc.response["Error"]["Code"]
    except Exception:  # noqa: BLE001
        return type(exc).__name__


def _aws_err(exc, target, action) -> int:
    code = _code(exc)
    msg = "wake_box: AWS error %s on %s" % (code, action)
    if code in ("UnauthorizedOperation", "AccessDenied", "AccessDeniedException"):
        msg += (" - the inline policy %s is missing or wrong on this box's role"
                % POLICY)
    print(msg)
    _log(target, action, "aws-error " + code)
    return 3


def _find(ec2, name):
    r = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [name]}])
    out = []
    for res in r.get("Reservations", []):
        for i in res.get("Instances", []):
            if i.get("State", {}).get("Name") == "terminated":
                continue
            out.append(i)
    return out


def _et(ts) -> str:
    if ts is None:
        return "?"
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return ts.astimezone(ET).strftime("%Y-%m-%d %H:%M ET")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Wake or stop one allowed TEST box.")
    ap.add_argument("name")
    ap.add_argument("--status", action="store_true", help="read only; never starts or stops")
    ap.add_argument("--stop", action="store_true", help="stop it (refused in session hours)")
    ap.add_argument("--during-session", action="store_true",
                    help="allow --stop 09:25-16:10 ET on a weekday - ONLY on the operator's word")
    ap.add_argument("--wait", type=int, default=120, help="seconds to wait for the end state")
    a = ap.parse_args(argv)
    if a.status and a.stop:
        print("wake_box: REFUSED - --status and --stop together")
        return 2
    action = "status" if a.status else ("stop" if a.stop else "wake")

    if a.stop and not a.during_session and in_session(now_et()):
        print("wake_box: REFUSED - a stop between %02d:%02d and %02d:%02d ET on a weekday needs"
              " --during-session, given only on the operator's word" % (SESSION_START + SESSION_END))
        _log(a.name, action, "refused session-hours")
        return 2

    if a.name not in ALLOWED:
        print("wake_box: REFUSED - %r is not on the allow-list %s"
              % (a.name, sorted(ALLOWED)))
        _log(a.name, action, "refused not-allowed")
        return 2

    try:
        ec2 = make_client()
        found = _find(ec2, a.name)
    except Exception as exc:  # noqa: BLE001
        return _aws_err(exc, a.name, "DescribeInstances")

    if len(found) != 1:
        ids = ", ".join(i["InstanceId"] for i in found) or "none"
        print("wake_box: REFUSED - %d instance(s) tagged Name=%s (%s); exactly one required"
              % (len(found), a.name, ids))
        _log(a.name, action, "refused matches=%d %s" % (len(found), ids))
        return 2
    inst = found[0]
    iid = inst["InstanceId"]
    me = self_instance_id()
    if me and iid == me:
        print("wake_box: REFUSED - %s (%s) is THIS instance" % (a.name, iid))
        _log(a.name, action, "refused self " + iid)
        return 2
    state = inst.get("State", {}).get("Name", "?")

    if a.status:
        print("%s  %s  state=%s  launched %s"
              % (a.name, iid, state, _et(inst.get("LaunchTime"))))
        _log(a.name, action, "state=" + state)
        return 0
    if a.stop:
        if state == "stopped":
            print("wake_box: %s (%s) is already stopped - nothing sent" % (a.name, iid))
            _log(a.name, action, "already stopped")
            return 0
        if state == "stopping":
            print("wake_box: %s (%s) is already stopping - waiting" % (a.name, iid))
            return _wait(ec2, a.name, iid, "stopping", "stopped", a.wait, action)
        if state != "running":
            print("wake_box: REFUSED - %s (%s) is %s; retry once it is running"
                  % (a.name, iid, state))
            _log(a.name, action, "refused state=" + state)
            return 2
        try:
            ec2.stop_instances(InstanceIds=[iid])      # never Force, Hibernate or terminate
        except Exception as exc:  # noqa: BLE001
            return _aws_err(exc, a.name, "StopInstances")
        print("wake_box: StopInstances sent for %s (%s)" % (a.name, iid))
        return _wait(ec2, a.name, iid, state, "stopped", a.wait, action)

    if state in ("running", "pending"):
        print("wake_box: %s (%s) is already %s - nothing started" % (a.name, iid, state))
        _log(a.name, action, "already " + state)
        return 0
    if state != "stopped":
        print("wake_box: REFUSED - %s (%s) is %s; retry once it has stopped"
              % (a.name, iid, state))
        _log(a.name, action, "refused state=" + state)
        return 2

    try:
        ec2.start_instances(InstanceIds=[iid])
    except Exception as exc:  # noqa: BLE001
        return _aws_err(exc, a.name, "StartInstances")
    print("wake_box: StartInstances sent for %s (%s)" % (a.name, iid))
    return _wait(ec2, a.name, iid, state, "running", a.wait, action)


def _wait(ec2, name, iid, last, goal, wait, action) -> int:
    deadline = time.time() + wait
    while True:
        try:
            cur = _find(ec2, name)
        except Exception as exc:  # noqa: BLE001
            return _aws_err(exc, name, "DescribeInstances")
        now = cur[0] if cur else {}
        st = now.get("State", {}).get("Name", "?")
        if st != last:
            print("  %s -> %s" % (last, st))
            last = st
        if st == goal:
            if goal == "running":
                print("running  %s  private IP %s" % (iid, now.get("PrivateIpAddress", "?")))
                _log(name, action, "started running " + iid)
            else:
                print("stopped  %s" % iid)
                _log(name, action, "stopped " + iid)
            return 0
        if time.time() >= deadline:
            print("wake_box: TIMED OUT after %ds - %s is %s" % (wait, iid, st))
            _log(name, action, "timeout state=" + st)
            return 4
        time.sleep(POLL_S)

if __name__ == "__main__":
    sys.exit(main())
