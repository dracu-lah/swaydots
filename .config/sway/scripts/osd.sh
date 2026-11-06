#!/bin/sh
# Volume, mic and brightness keys with a dunst progress popup.
# Usage: osd.sh volume up|down|mute  |  osd.sh mic  |  osd.sh brightness up|down

notify() { tag=$1; shift; notify-send -h "string:x-canonical-private-synchronous:$tag" "$@"; }
muted()  { wpctl get-volume "$1" | grep -q MUTED && echo Muted || echo Unmuted; }

case "$1" in
    volume)
        sink=@DEFAULT_AUDIO_SINK@
        case "$2" in
            up)   wpctl set-volume -l 1.5 "$sink" 5%+ ;;
            down) wpctl set-volume "$sink" 5%- ;;
            mute) wpctl set-mute "$sink" toggle; notify volume Volume "$(muted "$sink")"; exit ;;
        esac
        pct=$(wpctl get-volume "$sink" | awk '{print int($2*100)}')
        notify volume Volume -h "int:value:$pct"
        ;;
    mic)
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
        notify mic Microphone "$(muted @DEFAULT_AUDIO_SOURCE@)"
        ;;
    brightness)
        case "$2" in
            up)   step=+5% ;;
            down) step=5%- ;;
        esac
        pct=$(brightnessctl -m s "$step" | cut -d, -f4 | tr -d %)
        notify brightness Brightness -h "int:value:$pct"
        ;;
esac
