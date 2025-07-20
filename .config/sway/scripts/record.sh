#!/bin/env bash

# Check if wf-recorder is already running
if pgrep -x "wf-recorder" >/dev/null; then
  pkill -INT -x wf-recorder
  notify-send -h string:wf-recorder:record -t 1000 "Finished Recording"
  exit 0
fi

# Generate a timestamp for the filename
dateTime=$(date +%Y-%m-%d_%H-%M-%S)

# Start recording a selected region with audio (adjust audio device as needed)
# For full screen, remove -g "$(slurp)"
# wf-recorder -g "$(slurp)" -a "alsa_input.pci-0000_00_1f.3.analog-stereo.monitor" -f "$HOME/Videos/recording_${dateTime}.mp4" &
wf-recorder -a "alsa_input.pci-0000_00_1f.3.analog-stereo.monitor" -f "$HOME/Videos/recording_${dateTime}.mp4" &

notify-send -h string:wf-recorder:record -t 1000 "Recording started..."
