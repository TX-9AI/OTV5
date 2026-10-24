#!/bin/bash
# tools/guarded.sh  v1.0
# v1.0  2026-10-04  OTV4TEST r250 — MOVED INTO THE REPO from /var/tmp/breakout_exit_wargame/guarded.sh (the operator,
#       2026-10-04: "finish what you can"), with ONE FIX: the old script ended `wait $P; echo "rc=$?"`, so it
#       always exited 0 - a study killed by the guard, or one that crashed, looked like a success to its caller.
#       It now exits with the child's code, and with 137 when the guard killed it.
# Runs "$@" under an RSS watchdog. The box has ~908 MB and runs the bot.
#   GUARD_KB  the RSS ceiling in KB (default 358400 = 350 MB)
# The child volunteers as the FIRST out-of-memory victim (oom_score_adj 1000), so the kernel never picks the bot:
# on 2026-09-27 the bot's oom_score was 714 against a study worker's 681.
# Usage:  bash tools/guarded.sh python3 my_study.py --args
"$@" & P=$!
echo 1000 > /proc/$P/oom_score_adj 2>/dev/null
KILLED=0
while kill -0 $P 2>/dev/null; do
  R=$(ps -o rss= -p $P 2>/dev/null | tr -d ' ')
  if [ -n "$R" ] && [ "$R" -gt "${GUARD_KB:-358400}" ]; then
    echo "WATCHDOG: RSS ${R}KB > ${GUARD_KB:-358400}KB - killed $P" >&2
    kill $P; KILLED=1
  fi
  sleep 2
done
wait $P; RC=$?
[ "$KILLED" = 1 ] && RC=137
echo "rc=$RC" >&2
exit $RC
