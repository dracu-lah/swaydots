# swaydots: agent notes

Dotfiles for sway on a Dell Latitude 7430. `setup.sh` and the README target Arch (pacman/yay); the
laptop currently runs Fedora 43. Use `dnf` equivalents there.

## Layout

- `.config/`: stowed into `$HOME` with `stow .` (sway, waybar, scripts in `.config/sway/scripts`).
- `system/etc/`: root-owned configs, copied by `setup.sh` (not stowed). Keep these in sync when `/etc` changes.
- `system/bin/`: root diagnostics (`cpu-throttle-diag.sh`, `dell-bios.sh`). Run them in a real terminal: sudo needs a TTY.
- `docs/`: runbooks. Start with `docs/laptop-performance.md` for slowness, battery, heat or charger issues.
- `.stow-local-ignore`: lists everything that must not be symlinked into `$HOME`.

## Rules

- One CPU power manager: auto-cpufreq. Never enable tlp, tuned or power-profiles-daemon next to it.
- Do not use the `performance` governor in auto-cpufreq; it overrides EPP. Use powersave + EPP.
- Battery charge limits are set in the BIOS (Custom 50/80), not by auto-cpufreq.
- Waybar's battery module only mirrors `/sys/class/power_supply`. A wrong charging icon is a
  firmware/charger issue, not a waybar bug.
- `Super+Shift+P` (`power-profile.sh`) cycles the auto-cpufreq override through a NOPASSWD sudoers rule for `/usr/local/bin/auto-cpufreq`.
