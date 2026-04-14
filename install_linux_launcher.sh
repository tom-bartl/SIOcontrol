#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/launch_sio.sh"
APP_DIR="$HOME/.local/share/applications"
APP_FILE="$APP_DIR/sio-control.desktop"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP_FILE="$DESKTOP_DIR/SIO Control.desktop"
LIBFM_CONF="$HOME/.config/libfm/libfm.conf"

mkdir -p "$APP_DIR"
chmod +x "$LAUNCHER"

cat > "$APP_FILE" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=SIO Control
Comment=Run the Shake-it-off control GUI
Exec=$LAUNCHER
Path=$SCRIPT_DIR
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Utility;
StartupNotify=true
DESKTOP

chmod +x "$APP_FILE"

if [[ -d "$DESKTOP_DIR" ]]; then
  cp "$APP_FILE" "$DESKTOP_FILE"
  chmod +x "$DESKTOP_FILE"

  # GNOME and some file managers require a trusted flag for desktop launchers.
  if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_FILE" metadata::trusted true >/dev/null 2>&1 || true
  fi
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

# For GNOME/Nautilus, launch executable files by default.
if command -v gsettings >/dev/null 2>&1; then
  if gsettings writable org.gnome.nautilus.preferences executable-text-activation >/dev/null 2>&1; then
    gsettings set org.gnome.nautilus.preferences executable-text-activation 'launch' >/dev/null 2>&1 || true
  fi
fi

# Raspberry Pi OS (PIXEL/PCManFM): disable open/execute prompt for executables.
mkdir -p "$(dirname "$LIBFM_CONF")"
if [[ -f "$LIBFM_CONF" ]]; then
  if grep -q '^quick_exec=' "$LIBFM_CONF"; then
    sed -i 's/^quick_exec=.*/quick_exec=1/' "$LIBFM_CONF"
  else
    printf '\n[config]\nquick_exec=1\n' >> "$LIBFM_CONF"
  fi
else
  cat > "$LIBFM_CONF" <<LIBFM
[config]
quick_exec=1
LIBFM
fi

echo "Launcher installed: $APP_FILE"
if [[ -d "$DESKTOP_DIR" ]]; then
  echo "Desktop shortcut: $DESKTOP_FILE"
fi
echo "Set libfm quick_exec=1 in: $LIBFM_CONF"
echo "If prompt still appears, log out and log back in once."
