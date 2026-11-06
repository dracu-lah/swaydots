#!/bin/bash
# Read-only diagnosis of CPU throttling: BD PROCHOT bit, perf limit reasons, real clock under load.
# Run in a real terminal (sudo needs a TTY), ideally at the moment things feel slow.
# Output is also saved to ~/diag.log.
sudo -v || { echo "sudo needs a real terminal: run this in a terminal emulator, not via '!'"; exit 1; }
exec > >(tee ~/diag.log) 2>&1
rpm -q msr-tools >/dev/null 2>&1 || command -v rdmsr >/dev/null || sudo dnf install -y -q msr-tools
sudo modprobe msr
ps=/sys/class/power_supply
echo "== AC online: $(cat $ps/AC/online)  BAT0: $(cat $ps/BAT0/status)  usbc_online: $(cat $ps/ucsi*/online 2>/dev/null | tr '\n' ' ')"
echo "== EPP: $(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference)  platform_profile: $(cat /sys/firmware/acpi/platform_profile)"
v=$(sudo rdmsr -p0 0x1FC); echo "== MSR 0x1FC = 0x$v  BD_PROCHOT enabled bit: $(( 0x$v & 1 ))"
r=$(sudo rdmsr -p0 0x64F 2>/dev/null) && {
  echo "== perf limit reasons 0x64F = 0x$r"
  for b in 0:PROCHOT 1:Thermal 4:Residency 5:RATL 6:VR_Therm 7:VR_TDC 8:Other 10:PL1 11:PL2 12:MaxTurbo 13:TurboAtten; do
    n=${b%%:*}
    (( (0x$r>>n)&1 )) && echo "   ACTIVE now: ${b#*:}"
    (( (0x$r>>(n+16))&1 )) && echo "   logged:     ${b#*:}"
  done
}
for i in 1 2 3 4; do timeout 6 sh -c 'while :; do :; done' & done
sudo turbostat --quiet --Summary --show Busy%,Bzy_MHz,PkgWatt,PkgTmp --interval 2 --num_iterations 2
wait
