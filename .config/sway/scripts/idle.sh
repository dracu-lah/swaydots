#!/bin/sh
# Called by swayidle. Usage: idle.sh <bat|any> <screen-off|suspend>
# "bat" actions only run on battery, so one swayidle covers AC and battery
# without polling the charger.

on_ac() {
    for f in /sys/class/power_supply/*; do
        [ "$(cat "$f/type" 2>/dev/null)" = Mains ] && [ "$(cat "$f/online" 2>/dev/null)" = 1 ] && return 0
    done
    return 1
}

[ "$1" = bat ] && on_ac && exit 0

case "$2" in
    screen-off) swaymsg 'output * power off' >/dev/null ;;
    suspend)    systemctl suspend ;;
esac
