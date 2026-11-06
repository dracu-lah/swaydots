#!/bin/bash
# Dell BIOS settings from Linux (dell-wmi-sysman). Works while no BIOS admin password is set.
#   dell-bios.sh          -> show current vs recommended (changes nothing)
#   dell-bios.sh apply    -> set the recommended values (take effect after reboot)
sudo -v || { echo "sudo needs a real terminal"; exit 1; }
A=/sys/class/firmware-attributes/dell-wmi-sysman/attributes
declare -A R=(
  [SpeedShift]=Enabled             # fast clock changes, needed for EPP
  [Speedstep]=Enabled
  [CStatesCtrl]=Enabled            # idle power saving, also needed for full turbo
  [TurboMode]=Enabled
  [PowerWarn]=Enabled              # warns at boot when a charger is underpowered
  [AdvBatteryChargeCfg]=Disabled   # conflicts with Custom charge limits
  [PeakShiftCfg]=Disabled
  [BlockSleep]=Disabled
  [DynamicWirelessTransmitPower]=Enabled
  [PrimaryBattChargeCfg]=Custom    # uses CustomChargeStart/Stop (50/80); auto-cpufreq cannot set Dell thresholds
)
printf '%-30s %-16s %s\n' SETTING CURRENT RECOMMENDED
for k in "${!R[@]}" ThermalManagement CustomChargeStart CustomChargeStop; do
  [ -d "$A/$k" ] || continue
  printf '%-30s %-16s %s\n' "$k" "$(sudo cat $A/$k/current_value)" "${R[$k]:-(left as is)}"
done
[ "$1" = apply ] || { echo; echo "Nothing changed. Run '$0 apply' to set these."; exit 0; }
for k in "${!R[@]}"; do
  [ -d "$A/$k" ] || continue
  [ "$(sudo cat $A/$k/current_value)" = "${R[$k]}" ] && continue
  echo "${R[$k]}" | sudo tee "$A/$k/current_value" >/dev/null && echo "set $k=${R[$k]}"
done
echo "pending reboot: $(cat $A/pending_reboot 2>/dev/null)"
