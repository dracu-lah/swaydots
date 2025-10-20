# =============================================
# AUTO DARK MODE CONFIGURATION
# =============================================

# Set environment variables for dark theme
env = GTK_THEME=Adwaita-dark
env = QT_STYLE_OVERRIDE=Adwaita-Dark
env = QT_QPA_PLATFORMTHEME=qt5ct
env = ELECTRON_ENABLE_DARK_MODE=1
env = MOZ_ENABLE_WAYLAND=1
env = MOZ_DARKMODE=1
env = WEBKIT_FORCE_DARK_MODE=1
env = BAMF_DARK_THEME=1
env = COLORFGBG="15;0"

# Apply GTK dark theme settings
exec_always gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'
exec_always gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'
exec_always gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita'
exec_always gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
exec_always gsettings set org.gnome.desktop.interface cursor-size 24

# Additional dark mode preferences
exec_always gsettings set org.gnome.desktop.wm.preferences theme 'Adwaita-dark'
exec_always gsettings set org.gnome.settings-daemon.plugins.color night-light-enabled true

# Firefox specific dark mode (if using Firefox)
exec_always [ -f ~/.mozilla/firefox/*.default-release/user.js ] && echo 'user_pref("widget.content.gtk-theme-override", "Adwaita-dark");' >>~/.mozilla/firefox/*.default-release/user.js || true
