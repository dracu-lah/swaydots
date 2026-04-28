#!/bin/bash

WLSUNSET_PID=$(pgrep -x wlsunset 2>/dev/null)

case "$1" in
  status)
    if [ -z "$WLSUNSET_PID" ]; then
      echo "󱩍"
    else
      echo "󰛨"
    fi
    ;;
  toggle)
    if [ -z "$WLSUNSET_PID" ]; then
      setsid -f wlsunset -t 4000 -T 6500 -S 00:00 -s 00:01 -d 1 </dev/null >/dev/null 2>&1
    else
      kill "$WLSUNSET_PID"
    fi
    ;;
  *)
    "$0" status
    ;;
esac
