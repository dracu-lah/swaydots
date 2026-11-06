# Laptop performance and battery (Dell Latitude 7430)

Hardware: i7-1265U (10C/12T, 4.8 GHz boost), 30 GB RAM, WD SN570 NVMe, Iris Xe, Fedora 43, sway.

## Known issue: everything slow, CPU stuck at 400 MHz

- **Symptom:** apps and browsers take seconds to open (Chromium 2.6–3.6 s instead of 0.3 s), boot about 1m23s.
  Waybar shows a charging icon while unplugged.
- **Cause (2026-11-07):** the firmware asserts BD PROCHOT and clamps the CPU to 400 MHz. Triggered by a
  multi-port GaN charger: power renegotiation makes the EC see a weak or unknown adapter. It can stay
  latched after unplugging, and the AC state reads "online" with no charger.
- **Fix:** use the Dell 65 W charger, or the GaN's main port only with nothing else plugged in, and a 100 W
  (5 A) cable. EC reset if it is stuck: power off, unplug, hold power for 30 s.
- **Not a fix:** changing distro (it is firmware). Clearing the PROCHOT bit (`wrmsr 0x1FC`) is a last
  resort: it removes a hardware safety signal and resets on reboot.
- After the fix: Chromium 0.28 s, Zen 0.35 s, boot 37 s.

## Quick checks (no root)

```bash
cat /sys/class/power_supply/AC/online /sys/class/power_supply/BAT0/status   # 0 + Discharging when unplugged
grep MHz /proc/cpuinfo | sort -k4 -n | tail -3                                # under load: >2000, never 400
stat -c %y /var/run/auto-cpufreq.stats                                        # updates every few seconds
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference        # battery: balance_power
cat /sys/class/power_supply/BAT0/charge_types                                  # [Custom]
systemd-analyze                                                                # about 37 s
```

## Deep check (root, real terminal)

- `system/bin/cpu-throttle-diag.sh`: BD PROCHOT bit, perf limit reasons (MSR 0x64F), turbostat under
  load. Run it the moment it feels slow. Output goes to `~/diag.log`.
  - Clamped: `ACTIVE now: PROCHOT` and Bzy_MHz about 400.
  - Normal: about 3.6 GHz on 4 threads; about 2.75 GHz all-core sustained at 97°C (thermal limit, by design).
- `system/bin/dell-bios.sh`: current vs recommended BIOS values; `apply` sets them from Linux.

## Power stack

- **auto-cpufreq** (the only CPU power manager). Config: `system/etc/auto-cpufreq.conf` -> `/etc/auto-cpufreq.conf`.
  - Charger: governor powersave + EPP balance_performance + platform profile performance (full boost, less heat).
    Governor `performance` forces EPP performance, so do not use it.
  - Battery: EPP balance_power, platform balanced, turbo auto, no max-frequency cap. A 1.8 GHz cap with
    turbo never made apps slow on battery.
  - Its charge thresholds do nothing on this Dell ("No supported battery device found"). Charge limits
    live in the BIOS: PrimaryBattChargeCfg=Custom, 50/80.
  - It froze once (2026-11-07, v3.0.0) and kept charger mode on battery. Check the stats file mtime.
    If it is stale: `sudo systemctl restart auto-cpufreq`.
- **thermald** on. **tlp** and **tuned** masked (they conflict). The powertop auto-tune unit exists but is disabled.
- **platform_profile** is the BIOS Thermal Management setting (performance = Ultra Performance), switched by auto-cpufreq.
- **zram:** zstd, 8 GB (`system/etc/zram-generator.conf`). Plus a 32 GB btrfs swapfile for hibernate.
- **Video decode:** VA-API works (iHD driver). Fedora's `/etc/chromium/chromium.conf` enables it; Zen uses Firefox defaults.

## Thermals

- Repasted with Arctic MX-4 (2026-11-07). PTM7950 is the long-term option (no pump-out).
- Under full load it hits 97°C in about 15 s. The fan stays at 0 rpm for the first ~25 s (Dell EC curve),
  then about 3,900 rpm. It drops from 97°C to 62°C 10 s after the load stops.
- On battery: about 59 W boost for 20 s, then about 22 W / 1.8 GHz all-core (Dell battery limit).

## BIOS (checked 2026-11-07, BIOS 1.37.0)

SpeedShift, SpeedStep, C-States and Turbo are Enabled. Adapter Warnings is Enabled. Advanced Battery
Charge, Peak Shift and Block Sleep are Disabled. Battery charge is Custom 50/80. Thermal Management is
driven by auto-cpufreq. No BIOS update in fwupd.
