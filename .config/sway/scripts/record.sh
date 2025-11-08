#!/usr/bin/env bash

# --- Configuration ---
audio_source="alsa_input.pci-0000_00_1f.3.analog-stereo.monitor"
# Use a specific output directory for recordings
output_dir="$HOME/Videos/SwayRecordings"
mkdir -p "$output_dir"

# --- 🛑 Stop Recording Condition ---
if pgrep -x "wf-recorder" >/dev/null; then
  pkill -INT -x wf-recorder
  notify-send -h string:wf-recorder:record -t 1000 "Finished Recording"
  exit 0
fi

# --- Start Recording ---

# Count the number of active (enabled) outputs
output_count=$(wlr-randr | grep -c "Enabled: yes")

dateTime=$(date +%Y-%m-%d_%H-%M-%S)
output_file="$output_dir/recording_${dateTime}.mp4"

# Base command
RECORD_COMMAND="wf-recorder -a \"$audio_source\" -f \"$output_file\""

if [ "$output_count" -gt 1 ]; then
  # 🖥️ Multi-Monitor Mode (Launches slurp for selection)
  # This is why you see the "overlay" - it's slurp waiting for input.
  GEOMETRY=$(slurp -o -s -f "%w,%h %x,%y" -r)

  if [ -z "$GEOMETRY" ]; then
    # User canceled slurp, exit gracefully
    notify-send -h string:wf-recorder:record -t 2000 "Recording Canceled by User"
    exit 0
  fi

  # Add the geometry flag to the command
  RECORD_COMMAND="$RECORD_COMMAND -g \"$GEOMETRY\""
  notify_message="Recording **selected region** (Multi-Monitor Mode)..."
else
  # 💻 Single-Monitor Mode (Records entire screen by default)
  # Since output_count is 1, wf-recorder captures that single screen.
  notify_message="Recording **full screen** (Single-Monitor Mode)..."
fi

# Execute the recording command in the background
eval "$RECORD_COMMAND" &

# Send notification
notify-send -h string:wf-recorder:record -t 3000 "$notify_message"
