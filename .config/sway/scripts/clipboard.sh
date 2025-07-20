#!/bin/bash

# Get clipboard history
HISTORY=$(cliphist list)

# Add "Clear History" option
MENU_OPTIONS="Clear Clipboard History\n$HISTORY"

# Present options with wofi
SELECTION=$(echo -e "$MENU_OPTIONS" | wofi -dmenu -p "Clipboard:")

# Act based on selection
if [ -z "$SELECTION" ]; then
  exit 0 # User cancelled
elif [ "$SELECTION" == "Clear Clipboard History" ]; then
  cliphist wipe
  notify-send "Clipboard" "History cleared."
else
  # Decode and copy the selected item
  echo "$SELECTION" | cliphist decode | wl-copy
  # notify-send "Clipboard" "Pasted: $(echo "$SELECTION" | head -n 1 | cut -c 1-50)..." # Show a snippet
fi
