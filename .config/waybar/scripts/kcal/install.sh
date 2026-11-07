#!/usr/bin/env bash
# Install kcal's dependencies and a starter config. Run from anywhere; the calendar stays where it is.
#   ./install.sh            packages (asks for sudo) + ~/.config/kcal/config.json
#   ./install.sh --no-deps  config only
set -euo pipefail

here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
conf_dir="${XDG_CONFIG_HOME:-$HOME/.config}/kcal"

deps() {
  if command -v dnf >/dev/null; then        # Fedora (tested on 43)
    sudo dnf install -y python3-gobject python3-cairo gtk3 gtk-layer-shell jq wl-clipboard rit-rachana-fonts
  elif command -v pacman >/dev/null; then   # Arch, EndeavourOS, Manjaro (untested)
    sudo pacman -S --needed python-gobject python-cairo gtk3 gtk-layer-shell jq wl-clipboard noto-fonts
  elif command -v apt-get >/dev/null; then  # Debian, Ubuntu, Mint, Pop!_OS (untested)
    sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 \
      jq wl-clipboard fonts-smc-rachana
  else
    cat <<'EOF'
Unknown package manager. Install these yourself:
  Python 3 with PyGObject and pycairo, GTK 3 and its GObject introspection data,
  gtk-layer-shell (optional: without it the popup is a plain window),
  jq (for clock.sh), wl-clipboard (optional, Wayland copy), a Malayalam font (Rachana or Noto Sans Malayalam).
EOF
  fi
}

[ "${1:-}" = "--no-deps" ] || deps

mkdir -p "$conf_dir"
if [ -e "$conf_dir/config.json" ]; then
  echo "kept $conf_dir/config.json"
else
  cp "$here/config.example.json" "$conf_dir/config.json"
  echo "wrote $conf_dir/config.json"
fi
chmod +x "$here/kcal.py" "$here/clock.sh"

tmp="$(mktemp --suffix=.png)"
if python3 "$here/kcal.py" --screenshot "$tmp"; then echo "render check: ok"; else echo "render check failed: see the error above"; fi
rm -f "$tmp"
cat <<EOF

Open it with:   $here/kcal.py --toggle
Bind that to a key or a bar click; see README.md for Waybar, Sway, Hyprland, i3, GNOME and KDE.
EOF
