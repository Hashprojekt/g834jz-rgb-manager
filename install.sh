#!/usr/bin/env bash
set -euo pipefail

APP_NAME="g834jz-rgb-manager"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

APP_DIR="$HOME/.local/lib/$APP_NAME"
DATA_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
DESKTOP_DIR="$HOME/.local/share/applications"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
    FORCE=1
fi

echo "G834JZ RGB Manager — installer"

MODEL="$(cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || true)"
if [[ "$MODEL" != *G834JZ* ]] && [[ "$FORCE" -ne 1 ]]; then
    echo
    echo "BŁĄD: ten instalator jest przeznaczony dla ASUS ROG Strix G834JZ."
    echo "Wykryty model: ${MODEL:-nieznany}"
    echo "Jeśli świadomie chcesz kontynuować: ./install.sh --force"
    exit 1
fi

for cmd in python3 systemctl install; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "BŁĄD: brak wymaganej komendy: $cmd"
        exit 1
    fi
done

if ! command -v asusctl >/dev/null 2>&1; then
    echo "BŁĄD: brak asusctl. Zainstaluj asusctl/asusd dla swojej dystrybucji."
    exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$HOME/RGB-backup/$(date +%F)/github-install-$STAMP"
mkdir -p "$BACKUP"

mkdir -p \
    "$APP_DIR" \
    "$DATA_DIR/profiles" \
    "$BIN_DIR" \
    "$CONFIG_DIR" \
    "$USER_SYSTEMD_DIR" \
    "$DESKTOP_DIR"

# Backup plików, które instalator może nadpisać.
for f in \
    "$BIN_DIR/g834jz-rgb-apply-default.py" \
    "$BIN_DIR/g834jz-temp-leds.py" \
    "$BIN_DIR/rog-profile-next" \
    "$BIN_DIR/gamemode-asus-start" \
    "$BIN_DIR/gamemode-asus-end" \
    "$USER_SYSTEMD_DIR/g834jz-rgb-manager.service" \
    "$USER_SYSTEMD_DIR/g834jz-rgb-default.service" \
    "$USER_SYSTEMD_DIR/g834jz-temp-leds.service" \
    "$DESKTOP_DIR/g834jz-rgb-manager.desktop"
do
    if [[ -e "$f" ]]; then
        cp -a "$f" "$BACKUP/"
    fi
done

# Aplikacja.
install -m 0644 "$ROOT_DIR/app.py" "$APP_DIR/app.py"
install -m 0644 "$ROOT_DIR/VERSION" "$APP_DIR/VERSION"
install -m 0644 "$ROOT_DIR/requirements.txt" "$APP_DIR/requirements.txt"

rm -rf "$APP_DIR/static" "$APP_DIR/templates"
cp -a "$ROOT_DIR/static" "$APP_DIR/"
cp -a "$ROOT_DIR/templates" "$APP_DIR/"

# Python venv.
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$APP_DIR/.venv"
fi

"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

# Skrypty użytkownika.
install -m 0755 "$ROOT_DIR/scripts/g834jz-rgb-apply-default.py" \
    "$BIN_DIR/g834jz-rgb-apply-default.py"
install -m 0755 "$ROOT_DIR/scripts/g834jz-temp-leds.py" \
    "$BIN_DIR/g834jz-temp-leds.py"
install -m 0755 "$ROOT_DIR/scripts/rog-profile-next" \
    "$BIN_DIR/rog-profile-next"

# Integracja GameMode.
if [[ -d "$ROOT_DIR/integrations/gamemode" ]]; then
    [[ -f "$ROOT_DIR/integrations/gamemode/gamemode-asus-start" ]] && \
        install -m 0755 "$ROOT_DIR/integrations/gamemode/gamemode-asus-start" \
        "$BIN_DIR/gamemode-asus-start"

    [[ -f "$ROOT_DIR/integrations/gamemode/gamemode-asus-end" ]] && \
        install -m 0755 "$ROOT_DIR/integrations/gamemode/gamemode-asus-end" \
        "$BIN_DIR/gamemode-asus-end"

    if [[ -f "$ROOT_DIR/integrations/gamemode/gamemode.ini" ]]; then
        if [[ ! -e "$CONFIG_DIR/gamemode.ini" ]]; then
            install -m 0644 "$ROOT_DIR/integrations/gamemode/gamemode.ini" \
                "$CONFIG_DIR/gamemode.ini"
        else
            install -m 0644 "$ROOT_DIR/integrations/gamemode/gamemode.ini" \
                "$CONFIG_DIR/gamemode-g834jz-rgb-manager.example.ini"
            echo "INFO: istniejącego ~/.config/gamemode.ini nie nadpisano."
        fi
    fi
fi

# Profile startowe — tylko brakujące.
if [[ -d "$ROOT_DIR/defaults/profiles" ]]; then
    for profile in "$ROOT_DIR"/defaults/profiles/*; do
        [[ -d "$profile" ]] || continue
        name="$(basename "$profile")"
        if [[ ! -e "$DATA_DIR/profiles/$name" ]]; then
            cp -a "$profile" "$DATA_DIR/profiles/$name"
        fi
    done
fi

# Bazowy snapshot RGB dla monitora M3/M4/M5.
BASE_PROFILE="$ROOT_DIR/defaults/profiles/01-final/g834jz-rgb-base-packets.json"
if [[ -f "$BASE_PROFILE" ]] && [[ ! -e "$CONFIG_DIR/g834jz-rgb-base-packets.json" ]]; then
    install -m 0644 "$BASE_PROFILE" "$CONFIG_DIR/g834jz-rgb-base-packets.json"
fi

# User systemd.
install -m 0644 "$ROOT_DIR/systemd/user/g834jz-rgb-manager.service" \
    "$USER_SYSTEMD_DIR/g834jz-rgb-manager.service"
install -m 0644 "$ROOT_DIR/systemd/user/g834jz-rgb-default.service" \
    "$USER_SYSTEMD_DIR/g834jz-rgb-default.service"
install -m 0644 "$ROOT_DIR/systemd/user/g834jz-temp-leds.service" \
    "$USER_SYSTEMD_DIR/g834jz-temp-leds.service"

# Systemowe elementy ASUS/RGB.
echo
echo "Instalacja usług systemowych wymaga sudo."

sudo install -m 0755 "$ROOT_DIR/scripts/g834jz-rgb-profile.py" \
    /usr/local/bin/g834jz-rgb-profile.py

sudo install -m 0644 "$ROOT_DIR/systemd/system/g834jz-rgb-profile.service" \
    /etc/systemd/system/g834jz-rgb-profile.service
sudo install -m 0644 "$ROOT_DIR/systemd/system/asus-aura-fix.service" \
    /etc/systemd/system/asus-aura-fix.service
sudo install -m 0644 "$ROOT_DIR/systemd/system/asus-kbd-max.service" \
    /etc/systemd/system/asus-kbd-max.service

sudo systemctl daemon-reload

# asusd jest wymagany przez sterowanie Aura.
sudo systemctl unmask asusd.service >/dev/null 2>&1 || true
sudo systemctl enable --now asusd.service

sudo systemctl enable --now \
    g834jz-rgb-profile.service \
    asus-aura-fix.service \
    asus-kbd-max.service

systemctl --user daemon-reload
systemctl --user enable \
    g834jz-rgb-default.service \
    g834jz-temp-leds.service \
    g834jz-rgb-manager.service

systemctl --user restart g834jz-rgb-default.service
systemctl --user restart g834jz-temp-leds.service
systemctl --user restart g834jz-rgb-manager.service

# Launcher KDE/GNOME.
cat > "$DESKTOP_DIR/g834jz-rgb-manager.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=G834JZ RGB Manager
Comment=ASUS ROG Strix G834JZ RGB Manager
Exec=xdg-open http://127.0.0.1:8765
Icon=preferences-desktop-color
Terminal=false
Categories=Settings;HardwareSettings;
EOF

chmod 0644 "$DESKTOP_DIR/g834jz-rgb-manager.desktop"

echo
echo "========================================"
echo " G834JZ RGB MANAGER ZAINSTALOWANY"
echo "========================================"
echo "Wersja:  $(cat "$APP_DIR/VERSION")"
echo "Panel:   http://127.0.0.1:8765"
echo "Aplikacja: $APP_DIR"
echo "Profile:   $DATA_DIR/profiles"
echo "Backup:    $BACKUP"
