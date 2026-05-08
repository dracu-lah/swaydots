# dGPU power & HDMI

HP Victus 16 — RTX 4050 Mobile. HDMI port is wired to the dGPU.

## Usage

```sh
dgpu on        # turns dGPU ON, reboots immediately
dgpu off       # turns dGPU OFF, reboots immediately
dgpu status    # check current + next-boot state
```

No sudo, no prompt — wired up via a sudoers drop-in. Default = OFF.
Idle ~6–7 W on battery with dGPU off.

## Sway keybind (optional)

```
bindsym $mod+Shift+g exec dgpu on
bindsym $mod+Shift+G exec dgpu off
```

## Install

```sh
sudo install -m 644 ~/dgpu-power.service /etc/systemd/system/dgpu-power.service
sudo install -m 755 ~/dgpu              /usr/local/bin/dgpu
sudo install -m 440 ~/dgpu-sudoers      /etc/sudoers.d/dgpu
sudo systemctl daemon-reload
sudo systemctl enable dgpu-power.service
rm ~/dgpu-power.service ~/dgpu ~/dgpu-sudoers
```

First time only — also drop `fbdev=1` from `/etc/modprobe.d/nvidia-pm.conf`
(leave `NVreg_DynamicPowerManagement=0x02` and `nvidia_drm modeset=1`),
then `sudo mkinitcpio -P && sudo reboot`.

## Files

- `/etc/systemd/system/dgpu-power.service` — PCI-removes the dGPU at early
  boot, before sway can hold a DRM fd on it.
- `/usr/local/bin/dgpu` — wrapper that flips `systemctl enable/disable` and
  reboots.
- `/etc/sudoers.d/dgpu` — NOPASSWD for the three commands the wrapper runs.
- `/etc/modprobe.d/nvidia-pm.conf` — `NVreg_DynamicPowerManagement=0x02` +
  `nvidia_drm modeset=1`. **No `fbdev=1`** (ghost framebuffer pinned the
  dGPU active and added ~7 W).
