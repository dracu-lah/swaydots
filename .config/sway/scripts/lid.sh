#!/bin/bash
# Lid close: suspend if on battery, blank display if on AC.

ac_online() {
    for f in /sys/class/power_supply/*/online; do
        [ -e "$f" ] || continue
        t="${f%online}type"
        [ -e "$t" ] && [ "$(cat "$t")" = "Mains" ] && [ "$(cat "$f")" = "1" ] && return 0
    done
    return 1
}

if ac_online; then
    swaymsg 'output eDP-1 disable'
else
    systemctl suspend
fi
