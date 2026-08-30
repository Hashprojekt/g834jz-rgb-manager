#!/usr/bin/env bash
set -euo pipefail

APP_NAME="g834jz-rgb-manager"

APP_DIR="$HOME/.local/lib/$APP_NAME"
DATA_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
DESKTOP_FILE="$HOME/.local/share/applications/g834jz-rgb-manager.desktop"

PURGE=0
if [[ "${1:-}" == "--purge" ]]; then
    PURGE=1
fi

echo "G834JZ RGB Manager — uninstall"

systemctl --user disable --now \
    g834jz-rgb-manager.service \
    g834jz-temp-leds.service \
    g834jz-rgb-default.service \
    >/dev/null 2>&1 || true

rm -f \
    "$USER_SYSTEMD_DIR/g834jz-rgb-manager.service" \
    "$USER_SYSTEMD_DIR/g834jz-temp-leds.service" \
    "$USER_SYSTEMD_DIR/g834jz-rgb-default.service" \
    "$BIN_DIR/g834jz-rgb-apply-default.py" \
    "$BIN_DIR/g834jz-temp-leds.py" \
    "$BIN_DIR/rog-profile-next" \
    "$BIN_DIR/gamemode-asus-start" \
    "$BIN_DIR/gamemode-asus-end" \
    "$DESKTOP_FILE"

systemctl --user daemon-reload

echo "Usuwanie usług systemowych wymaga sudo."

sudo systemctl disable --now \
    g834jz-rgb-profile.service \
    asus-aura-fix.service \
    asus-kbd-max.service \
    >/dev/null 2>&1 || true

sudo rm -f \
    /etc/systemd/system/g834jz-rgb-profile.service \
    /etc/systemd/system/asus-aura-fix.service \
    /etc/systemd/system/asus-kbd-max.service \
    /usr/local/bin/g834jz-rgb-profile.py

sudo systemctl daemon-reload

rm -rf "$APP_DIR"

if [[ "$PURGE" -eq 1 ]]; then
    rm -rf "$DATA_DIR"
    rm -f "$HOME/.config/g834jz-rgb-base-packets.json"
    echo "Usunięto również profile i dane użytkownika (--purge)."
else
    echo "Profile pozostawiono w: $DATA_DIR"
fi

echo "G834JZ RGB Manager został odinstalowany."
