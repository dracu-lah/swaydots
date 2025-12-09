#!/bin/bash

WLSUNSET_PID=$(pgrep wlsunset 2>/dev/null)

if [ "$1" == "status" ]; then
  if [ -z "$WLSUNSET_PID" ]; then

    echo ""
  else

    echo "󱩍"
  fi
  exit 0
fi

if [ "$1" == "toggle" ]; then
  if [ -z "$WLSUNSET_PID" ]; then
    wlsunset -t 4000 6500 &
  else
    kill "$WLSUNSET_PID"
  fi
  exit 0
fi

if [ -z "$1" ]; then
  "$0" status
fi
