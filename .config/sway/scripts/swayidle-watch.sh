#!/bin/bash
# Run swayidle with timeouts based on AC state. Restart on AC change.

LOCK_BG="$HOME/wallpapers/wallpaper.jpg"

ac_online() {
    for f in /sys/class/power_supply/*/online; do
        [ -e "$f" ] || continue
        t="${f%online}type"
        [ -e "$t" ] && [ "$(cat "$t")" = "Mains" ] && [ "$(cat "$f")" = "1" ] && return 0
    done
    return 1
}

start() {
    if ac_online; then
        # AC: relaxed (10 min screen off, 30 min suspend)
        swayidle -w \
            timeout 600  'swaymsg "output * dpms off"' \
              resume     'swaymsg "output * dpms on"' \
            timeout 1800 'systemctl suspend' \
            before-sleep "swaylock -f -i $LOCK_BG" &
    else
        # Battery: aggressive (2 min screen off, 3 min suspend)
        swayidle -w \
            timeout 120 'swaymsg "output * dpms off"' \
              resume    'swaymsg "output * dpms on"' \
            timeout 180 'systemctl suspend' \
            before-sleep "swaylock -f -i $LOCK_BG" &
    fi
    PID=$!
}

cleanup() { kill "$PID" 2>/dev/null; }
trap cleanup EXIT TERM INT

pkill -x swayidle 2>/dev/null
sleep 0.5
start

LAST=$(ac_online && echo ac || echo bat)
while sleep 5; do
    NOW=$(ac_online && echo ac || echo bat)
    if [ "$NOW" != "$LAST" ]; then
        kill "$PID" 2>/dev/null
        start
        LAST="$NOW"
    fi
done
