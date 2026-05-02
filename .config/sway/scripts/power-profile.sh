#!/bin/bash
# Cycle auto-cpufreq override: performance -> powersave -> reset (auto).
state=$(auto-cpufreq --get-state 2>/dev/null | awk '/Override status/ {print $3}')
case "$state" in
  performance) sudo auto-cpufreq --force=powersave   >/dev/null; msg="powersave" ;;
  powersave)   sudo auto-cpufreq --force=reset       >/dev/null; msg="auto (default)" ;;
  *)           sudo auto-cpufreq --force=performance >/dev/null; msg="performance" ;;
esac
notify-send -h string:x-canonical-private-synchronous:powerprofile "Power profile" "$msg"
