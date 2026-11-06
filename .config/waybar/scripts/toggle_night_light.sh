#!/bin/sh
# Night light (wlsunset). Usage: toggle_night_light.sh status|toggle

running() { pgrep -x wlsunset >/dev/null; }

# Wait up to 1s for wlsunset to reach the wanted state ($1: on|off)
wait_for() {
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if running; then [ "$1" = on ] && return; else [ "$1" = off ] && return; fi
        sleep 0.1
    done
}

case "$1" in
    toggle)
        if running; then
            pkill -x wlsunset
            wait_for off
        else
            setsid -f wlsunset -t 4000 -T 6500 -S 00:00 -s 00:01 -d 1 </dev/null >/dev/null 2>&1
            wait_for on
        fi
        # Refresh the waybar icon now (module "signal": 9)
        pkill -RTMIN+9 waybar
        ;;
    *)
        if running; then echo "󰛨"; else echo "󱩍"; fi
        ;;
esac
