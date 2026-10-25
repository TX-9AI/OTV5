#!/usr/bin/env bash
# deploy/purge_feed_guard.sh — v5.0
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
# v1.0  2026-10-12  OTV4TEST r275 (OPS.23) — THE PURGE STOPS THE CANDLE-FEED AROUND ITSELF.
#       Since 2026-10-08 the 16:05 ET retention purge's VACUUM of feed_store.db held the
#       database longer than the feed's 5 s sqlite wait: the feed died on "database is
#       locked" and systemd restarted it 7-18 times in ~4 minutes, every restart replaying
#       candle history (on 10-12 that replay re-wrote two repaired 10-08 bars before r271's
#       guard was live). The midnight halt shuts the MACHINE down, so there is no overnight
#       window with the box up and the feed down; instead the purge's own unit stops the
#       feed first and starts it after - one deliberate ~4 minute gap after the close,
#       one replay, instead of a crash loop. The operator, 2026-10-12 16:15 ET: "Yes, fix
#       it all. Land what you can."
#   stop  : only if candle-feed is ACTIVE, stop it and drop a flag.
#   start : only if THAT flag exists, start candle-feed and remove the flag - a feed the
#           operator stopped by hand stays stopped.
# It never fails its caller: a guard that could fail the purge, or leave the unit failed,
# would trade one outage for another. Every action is printed for the purge log.
FLAG="${OT_PURGE_FEED_FLAG:-/run/optbot-purge-stopped-feed}"
UNIT="candle-feed.service"
case "${1:-}" in
  stop)
    if systemctl is-active --quiet "$UNIT"; then
      if systemctl stop "$UNIT"; then
        : > "$FLAG" && echo "[purge-feed-guard] stopped $UNIT for the purge"
      else
        echo "[purge-feed-guard] WARNING: could not stop $UNIT - the purge runs with it up"
      fi
    else
      echo "[purge-feed-guard] $UNIT is not active - nothing stopped, nothing will be started"
    fi ;;
  start)
    if [ -e "$FLAG" ]; then
      rm -f "$FLAG"
      if systemctl start "$UNIT"; then
        echo "[purge-feed-guard] started $UNIT after the purge"
      else
        echo "[purge-feed-guard] ERROR: could not start $UNIT after the purge"
      fi
    else
      echo "[purge-feed-guard] this purge did not stop $UNIT - leaving it as it is"
    fi ;;
  *) echo "[purge-feed-guard] usage: $0 stop|start" ;;
esac
exit 0
