#!/bin/bash
# Click-target for waybar battery module. Dumps stats that don't fit the bar tooltip.
B=/sys/class/power_supply/BAT0
full=$(cat "$B/charge_full")
design=$(cat "$B/charge_full_design")
vmin=$(cat "$B/voltage_min_design")
health=$(( 100 * full / design ))
full_wh=$(awk "BEGIN{printf \"%.1f\", $full*$vmin/1e12}")
design_wh=$(awk "BEGIN{printf \"%.1f\", $design*$vmin/1e12}")
start=$(cat "$B/charge_control_start_threshold" 2>/dev/null || echo "?")
stop=$(cat "$B/charge_control_end_threshold" 2>/dev/null || echo "?")
temp=$(awk "BEGIN{printf \"%.1f\", $(cat "$B/temp")/10}")
mfg=$(printf "%s-%02d-%02d" "$(cat "$B/manufacture_year")" "$(cat "$B/manufacture_month")" "$(cat "$B/manufacture_day")")

notify-send "Battery $(cat "$B/model_name")" "\
Capacity:  $(cat "$B/capacity")% ($(cat "$B/status"))
Health:    ${health}% (${full_wh} Wh / ${design_wh} Wh design)
Cycles:    $(cat "$B/cycle_count")
Threshold: ${start}% – ${stop}%
Temp:      ${temp}°C
Mfg:       ${mfg}"
