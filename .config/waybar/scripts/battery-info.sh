#!/bin/bash
# Click-target for waybar battery module. Dumps stats that don't fit the bar tooltip.
B=/sys/class/power_supply/BAT0
full=$(cat "$B/energy_full")
design=$(cat "$B/energy_full_design")
health=$(( 100 * full / design ))
full_wh=$(awk "BEGIN{printf \"%.1f\", $full/1e6}")
design_wh=$(awk "BEGIN{printf \"%.1f\", $design/1e6}")

notify-send "Battery $(cat "$B/model_name")" "\
Capacity: $(cat "$B/capacity")% ($(cat "$B/status"))
Health:   ${health}% (${full_wh} Wh / ${design_wh} Wh design)
Cycles:   $(cat "$B/cycle_count")
Mfr:      $(cat "$B/manufacturer")"
