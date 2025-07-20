#!/bin/bash

# Define the Unicode character for a small circle/dot
# You might need a font like Font Awesome or Nerd Fonts for these to display correctly
RECORDING_ICON="●" # A simple solid circle character
STOPPED_ICON="●"   # Same for consistency, color will differentiate

# Define colors for Pango markup
RECORDING_COLOR="#e06c75" # Red
STOPPED_COLOR="#61afef"   # Blue

# Check if wf-recorder is running
if pgrep -x "wf-recorder" >/dev/null; then
  # wf-recorder is running
  # Use Pango markup for colored text
  TEXT_OUTPUT="<span foreground='${RECORDING_COLOR}'>${RECORDING_ICON}</span>"
  CLASS_OUTPUT="recording"
  TOOLTIP_OUTPUT="Recording..."
# else
#   # wf-recorder is not running
#   TEXT_OUTPUT="<span foreground='${STOPPED_COLOR}'>${STOPPED_ICON}</span>"
#   CLASS_OUTPUT="stopped"
#   TOOLTIP_OUTPUT="Not Recording"
fi

# Output the JSON
echo "{\"text\": \"${TEXT_OUTPUT}\", \"class\": \"${CLASS_OUTPUT}\", \"tooltip\": \"${TOOLTIP_OUTPUT}\"}"
