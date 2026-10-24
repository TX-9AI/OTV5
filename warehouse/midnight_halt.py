#!/usr/bin/env python3
"""warehouse/midnight_halt.py — v1.1

v1.1 (2026-09-20) — OTV4TEST r67 / BOX.9 + BOX.10. TWO THINGS THIS COULD NOT
SAY. (1) IT NEVER NAMED ITSELF: the bot's STOPPED alert read "systemctl
stop/restart" for a hand stop, a bake and this backstop alike, so the operator
could only tell them apart BY THE CLOCK. It now stamps `HALT_CAUSE` through
`utils/shutdown_cause.record()` and the bot's SIGTERM handler reads it — best
effort, wrapped, and it can never prevent the halt. (2) IT COULD NOT TELL
ITSELF IT HAD FAILED: the `subprocess.run` result was captured and discarded
and `main()` returned 0 regardless, so a refused `sudo` finished SUCCESSFULLY
and the box billed all night with the journal saying "halting". The return code
is read, a failure logs at ERROR and exits non-zero so the UNIT goes to failed.
⚠️ A zero is still not proof the box went down — see the note at the call site.

v1.0 (2026-09-06) — r289 / EOD.3. IF THIS BOX IS STILL UP AT MIDNIGHT ET, STOP.

Operator: *"We have a self-directed drain and shutdown at 16:45 if the conductor
held them up or was absent. I want an addition that takes any boxes down that
happen to still be up at midnight. I do sometimes work on them late & might
forget. So I want another self shutdown at midnight eastern time to catch
anything I accidentally left up. No drain, or anything else. Just stop, that's
it."*

🔑 THIS IS A BACKSTOP, NOT AN EOD PATH, AND THE DIFFERENCE IS THE WHOLE DESIGN.
`self_close.py` at 16:45 drains to S3, VERIFIES, and deliberately STAYS UP IF
SHORT — because "a box that shuts down on unverified data is worse than one that
stays up: the local store is the only copy left, and a stopped box cannot be
asked anything." That reasoning is about the CLOSE. By midnight the close is
seven hours gone; whatever is still running is running for a reason nobody is
awake for.

⚠️ SO IT DELIBERATELY DOES NOT DRAIN, VERIFY, OR REPORT. Adding any of that
would recreate the 16:45 path with a second set of failure modes and a second
chance to hang — and a backstop that can hang is not a backstop. It stops the
instance. That is the entire contract.

🔑 IT HALTS THE SAME WAY `self_close` DOES — `sudo shutdown -h now` — and for
the reason recorded there: "the box stops the MACHINE, which is what actually
ends the EC2 bill. Stopping services would leave it running and idle, which is
the expensive half of the old failure mode." No IAM, no IMDS, no network: a
backstop whose value is that it cannot fail in novel ways must not acquire
dependencies the path it backs up does not have.

⚠️ IT OVERRIDES A DELIBERATE HOLD, AND THAT IS SAID OUT LOUD. A box held up by
`self_close` because its data was UNVERIFIED will be stopped by this at
midnight. Its data is then stranded until the next wake — not lost, but not
reachable either. The operator's instruction is explicit and the alternative is
a box that bills all weekend; the trade is recorded here so nobody has to
re-derive it.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [midnight_halt] %(message)s",
)
log = logging.getLogger(__name__)

# ⚠️ AN ESCAPE HATCH THAT SURVIVES A BAKE, because the one night the operator
# genuinely wants a box up all night is the night this must not fight him. Same
# sentinel idiom as FEED_MAINTENANCE and DRILL_DISK — a file, no restart.
# r67 — the text the operator sees on the STOPPED alert. It is a constant so
# the gate can assert the alert says this and not a paraphrase of it.
HALT_CAUSE = "midnight backstop — no drain"

HOLD_FLAG = os.environ.get(
    "OT_NO_MIDNIGHT_HALT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "NO_MIDNIGHT_HALT"))


def main(argv=None) -> int:
    dry = "--dry-run" in (argv if argv is not None else sys.argv[1:])

    if os.path.exists(HOLD_FLAG):
        # ⚠️ SILENT AND SUCCESSFUL. A held box is an EXPECTED condition, and a
        # timer that complains about one teaches the operator to stop reading
        # its log — §17's reasoning, applied to a journal rather than a page.
        log.info("HOLD flag present (%s) — staying up, by request.", HOLD_FLAG)
        return 0

    if dry:
        log.info("[dry-run] would run: sudo shutdown -h now")
        return 0

    # 🔑 `shutdown` — THE SAME MECHANISM `self_close` USES, AND FOR ITS REASON:
    # "the box stops the MACHINE, which is what actually ends the EC2 bill.
    # Stopping services would leave it running and idle, which is the expensive
    # half of the old failure mode." On these instances an OS halt stops the
    # instance, so this needs no IAM, no IMDS and no network.
    # ⚠️ A FIRST CUT READ THE INSTANCE ID FROM IMDS AND CALLED `stop_instances`
    # VIA boto3. That reinvented a solved problem and added two dependencies —
    # a metadata round trip and an IAM permission — to a backstop whose entire
    # value is that it cannot fail in novel ways.
    log.info("still up at midnight ET — halting (backstop, no drain)")

    # 🔑 r67 — SAY WHY, LOCALLY, BEFORE SIGNALLING. This unit carries no
    # `Environment=` lines and therefore no Telegram token (r287), and the
    # header above forbids acquiring one. So the cause is STAMPED and the bot's
    # own SIGTERM handler — which already has the token and a working path —
    # names it on the alert the operator receives anyway. Every shutdown used
    # to read "systemctl stop/restart", identical to a bake and to a hand stop.
    # ⚠️ BEST EFFORT, AND WRAPPED SO IT CAN NEVER PREVENT THE HALT. The import
    # and the write are both inside the guard: a backstop that failed to stop
    # the box because its LABELLING broke would be the cure killing the patient.
    try:
        from utils.shutdown_cause import record
        record(HALT_CAUSE)
    except Exception as exc:                                    # noqa: BLE001
        log.warning("could not stamp the shutdown cause (%s) — halting anyway", exc)

    r = subprocess.run(["sudo", "shutdown", "-h", "now"], capture_output=True)

    # 🔴 r67 — THE RESULT WAS CAPTURED AND THEN THROWN AWAY, and `main()`
    # returned 0 unconditionally. So this unit printed "halting" and finished
    # SUCCESSFULLY whether or not anything halted: a backstop that cannot tell
    # itself it failed, which is §0.5 in the one place the box's whole overnight
    # bill depends on. A non-zero exit now puts the UNIT into a failed state,
    # which is a signal systemd already carries and the journal already keeps.
    # ⚠️ THE HONEST LIMIT, STATED RATHER THAN IMPLIED: `shutdown -h now` returns
    # 0 as soon as it SCHEDULES the halt. A non-zero code is definite proof of
    # failure — the sudo/permission class, which is the realistic one — but a
    # zero is NOT proof of success. Proving the box actually went down can only
    # be done from somewhere that is not the box. Nothing PAGES on this yet
    # (BOX.10); it is visible in `systemctl status` and the journal.
    if r.returncode != 0:
        log.error("HALT FAILED — `sudo shutdown -h now` exited %d: %s | %s",
                  r.returncode,
                  (r.stderr or b"").decode("utf-8", "replace").strip() or "(no stderr)",
                  "THE BOX IS STILL UP AND WILL BILL UNTIL THE NEXT WAKE")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
