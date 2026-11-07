#!/usr/bin/env bash
# custom/clock: {text, tooltip}. Holidays come from the kcal cache (snapshot as fallback).
dir="$(dirname "$(readlink -f "$0")")/kcal"
store="$HOME/.cache/kcal/holidays.json"
[ -r "$store" ] || store="$dir/snapshot.json"
today=$(date +%F)
text=$(date '+%H:%M %d/%m/%Y')
full=$(date '+%A, %d %B %Y')
hol=$(jq -r --arg d "$today" '[.kerala[]? | select(.date == $d) | .name] | join(", ")' "$store" 2>/dev/null)
tip="$full"
[ -n "$hol" ] && tip="$full\n$hol"
jq -nc --arg t "$text" --arg tip "$(printf '%b' "$tip")" '{text: $t, tooltip: $tip}'
