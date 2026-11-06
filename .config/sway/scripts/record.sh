#!/bin/bash
# Toggle screen recording with system audio. One output: full screen.
# Several outputs: pick one with slurp. Tells waybar to refresh its icon.

refresh_bar() { pkill -RTMIN+8 waybar; }

if pgrep -x wf-recorder >/dev/null; then
    pkill -INT -x wf-recorder
    for _ in $(seq 30); do pgrep -x wf-recorder >/dev/null || break; sleep 0.1; done
    refresh_bar
    notify-send -h string:x-canonical-private-synchronous:record -t 1000 "Finished recording"
    exit 0
fi

dir="$HOME/Videos/SwayRecordings"
mkdir -p "$dir"
file="$dir/recording_$(date +%Y-%m-%d_%H-%M-%S).mp4"
# --audio=DEVICE must be attached: "-a DEVICE" ignores the device.
args=(--audio="$(pactl get-default-sink).monitor" -f "$file")

outputs=$(swaymsg -t get_outputs | jq '[.[] | select(.active)] | length')
if [ "$outputs" -gt 1 ]; then
    geometry=$(slurp -o -f "%x,%y %wx%h") || {
        notify-send -h string:x-canonical-private-synchronous:record -t 2000 "Recording canceled"
        exit 0
    }
    args+=(-g "$geometry")
    msg="Recording selected output"
else
    msg="Recording full screen"
fi

wf-recorder "${args[@]}" >/dev/null 2>&1 &
disown
refresh_bar
notify-send -h string:x-canonical-private-synchronous:record -t 3000 "$msg"
