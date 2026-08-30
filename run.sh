#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/lib/g834jz-rgb-manager"

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    echo "BŁĄD: aplikacja nie jest zainstalowana."
    echo "Uruchom najpierw ./install.sh"
    exit 1
fi

exec "$APP_DIR/.venv/bin/python" "$APP_DIR/app.py"
