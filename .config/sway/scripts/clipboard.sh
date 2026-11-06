#!/bin/sh
# Clipboard history picker (cliphist + wofi).

clear="Clear clipboard history"
choice=$({ echo "$clear"; cliphist list; } | wofi --dmenu -p "Clipboard:") || exit 0

if [ "$choice" = "$clear" ]; then
    cliphist wipe
    notify-send "Clipboard" "History cleared."
else
    printf '%s\n' "$choice" | cliphist decode | wl-copy
fi
