from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import unicodedata
import zipfile

from flask import Flask, jsonify, render_template, request, send_file


app = Flask(__name__)

APP_VERSION = "1.3"

HOME = Path.home()
APP_DATA = HOME / ".local/share/g834jz-rgb-manager"
PROFILES_DIR = APP_DATA / "profiles"
BACKUPS_DIR = APP_DATA / "backups"
PROFILE_HISTORY_DIR = APP_DATA / "profile-history"
STATE_FILE = APP_DATA / "state.json"
DEFAULT_FILE = APP_DATA / "default.json"
ACTIVE_BASE = HOME / ".config/g834jz-rgb-base-packets.json"
MONITOR_SERVICE = "g834jz-temp-leds.service"
MANAGER_SERVICE = "g834jz-rgb-manager.service"
PROTECTED_IDS = {"01-final", "02-codzienny"}
PROFILE_ID_RE = re.compile(r"^[0-9]{2,3}-[a-z0-9-]+$")

# Dynamic layer must always win over static profile editing.
DYNAMIC_KEYS = {"M3", "M4", "M5", "HOME"}

# Key -> one or more (packet, RGB offset) slots.
# Most regular key mappings come from asusctl rog-aura LedCode mapping.
# G834JZ-specific empirically confirmed overrides are kept for DELETE/HOME.
KEYMAP: dict[str, list[tuple[int, int]]] = {
    # ROG row
    "M1": [(0, 15)],
    "M2": [(0, 18)],
    "M3": [(0, 21)],
    "M4": [(0, 24)],
    "M5": [(0, 27)],

    # Function row
    "ESC": [(1, 24)],
    "F1": [(1, 30)],
    "F2": [(1, 33)],
    "F3": [(1, 36)],
    "F4": [(1, 39)],
    "F5": [(1, 45)],
    "F6": [(1, 48)],
    "F7": [(1, 51)],
    "F8": [(1, 54)],
    "F9": [(2, 12)],
    "F10": [(2, 15)],
    "F11": [(2, 18)],
    "F12": [(2, 21)],

    # G834JZ top-right block
    "DELETE": [(2, 27)],
    "PAUSE": [(2, 30)],
    "TOP_PRTSC": [(2, 33)],
    "HOME": [(2, 36)],

    # Number row
    "`": [(2, 39)],
    "1": [(2, 42)],
    "2": [(2, 45)],
    "3": [(2, 48)],
    "4": [(2, 51)],
    "5": [(2, 54)],
    "6": [(3, 9)],
    "7": [(3, 12)],
    "8": [(3, 15)],
    "9": [(3, 18)],
    "0": [(3, 21)],
    "-": [(3, 24)],
    "=": [(3, 27)],
    "BACKSPACE": [(3, 30), (3, 33), (3, 36)],

    # Q row
    "TAB": [(3, 54)],
    "Q": [(4, 9)],
    "W": [(4, 12)],
    "E": [(4, 15)],
    "R": [(4, 18)],
    "T": [(4, 21)],
    "Y": [(4, 24)],
    "U": [(4, 27)],
    "I": [(4, 30)],
    "O": [(4, 33)],
    "P": [(4, 36)],
    "[": [(4, 39)],
    "]": [(4, 42)],
    "\\": [(4, 45)],

    # A row
    "CAPS": [(5, 21)],
    "A": [(5, 24)],
    "S": [(5, 27)],
    "D": [(5, 30)],
    "F": [(5, 33)],
    "G": [(5, 36)],
    "H": [(5, 39)],
    "J": [(5, 42)],
    "K": [(5, 45)],
    "L": [(5, 48)],
    ";": [(5, 51)],
    "'": [(5, 54)],
    "ENTER": [(6, 9), (6, 12), (6, 15), (6, 18)],

    # Z row
    "LSHIFT": [(6, 36)],
    "Z": [(6, 42)],
    "X": [(6, 45)],
    "C": [(6, 48)],
    "V": [(6, 51)],
    "B": [(6, 54)],
    "N": [(7, 9)],
    "M": [(7, 12)],
    ",": [(7, 15)],
    ".": [(7, 18)],
    "/": [(7, 21)],
    "RSHIFT": [(7, 24)],

    # Bottom row
    "LCTRL": [(7, 51)],
    "FN": [(7, 54)],
    "WIN": [(8, 9)],
    "LALT": [(8, 12)],

    # G834JZ — empirically confirmed multi-LED Spacebar
    "SPACE": [(8, 15), (8, 18), (8, 21), (8, 24), (8, 27)],

    "RALT": [(8, 30)],
    "PRTSC": [(8, 33)],
    "RCTRL": [(8, 36)],

    # G834JZ — empirically confirmed arrow addresses
    "UP": [(7, 36)],
    "LEFT": [(8, 48)],
    "DOWN": [(8, 51)],
    "RIGHT": [(8, 54)],

    # G834JZ numeric keypad
    # NumLock i cyfry były już wcześniej potwierdzone na tym laptopie.
    # Operatory zajmują ciągłe wolne sloty tego samego fizycznego bloku.
    "NUMLOCK": [(3, 42)],
    "NUMDIV": [(3, 45)],
    "NUMMUL": [(3, 48)],
    "NUMMINUS": [(3, 51)],

    "NUM7": [(5, 9)],
    "NUM8": [(5, 12)],
    "NUM9": [(5, 15)],
    "NUMPLUS": [(5, 18)],

    "NUM4": [(6, 24)],
    "NUM5": [(6, 27)],
    "NUM6": [(6, 30)],

    "NUM1": [(7, 39)],
    "NUM2": [(7, 42)],
    "NUM3": [(7, 45)],
    "NUMENTER": [(7, 48)],

    "NUM0": [(9, 9)],
    "NUMDEL": [(9, 12)],
}

# Geometry mirrors installed g814ji-per-key_US.ron. None means display-only/unknown RGB address.
KEYBOARD_LAYOUT = [
    [
        {"id": "M1", "label": "M1"}, {"id": "M2", "label": "M2"},
        {"id": "M3", "label": "M3"}, {"id": "M4", "label": "M4"},
        {"id": "M5", "label": "M5"},
    ],
    [
        {"id": "ESC", "label": "Esc"}, {"gap": 1.15},
        *[{"id": f"F{i}", "label": f"F{i}"} for i in range(1, 5)], {"gap": .45},
        *[{"id": f"F{i}", "label": f"F{i}"} for i in range(5, 9)], {"gap": .45},
        *[{"id": f"F{i}", "label": f"F{i}"} for i in range(9, 13)],
        {"id": "DELETE", "label": "Del"},
        {"id": "PAUSE", "label": "Pause"},
        {"id": "TOP_PRTSC", "label": "PrtSc"},
        {"id": "HOME", "label": "Home"},
    ],
    [
        {"id": "`", "label": "`"}, *[{"id": str(i), "label": str(i)} for i in range(1, 10)],
        {"id": "0", "label": "0"}, {"id": "-", "label": "-"}, {"id": "=", "label": "="},
        {"id": "BACKSPACE", "label": "Backspace", "w": 2.0},
        {"gap": .3},
        {"id": "NUMLOCK", "label": "Num"}, {"id": "NUMDIV", "label": "/"},
        {"id": "NUMMUL", "label": "*"}, {"id": "NUMMINUS", "label": "-"},
    ],
    [
        {"id": "TAB", "label": "Tab", "w": 1.55},
        *[{"id": c, "label": c} for c in "QWERTYUIOP"],
        {"id": "[", "label": "["}, {"id": "]", "label": "]"},
        {"id": "\\", "label": "\\", "w": 1.45}, {"gap": .3},
        {"id": "NUM7", "label": "7"}, {"id": "NUM8", "label": "8"},
        {"id": "NUM9", "label": "9"}, {"id": "NUMPLUS", "label": "+", "h": 2.1},
    ],
    [
        {"id": "CAPS", "label": "Caps", "w": 1.85},
        *[{"id": c, "label": c} for c in "ASDFGHJKL"],
        {"id": ";", "label": ";"}, {"id": "'", "label": "'"},
        {"id": "ENTER", "label": "Enter", "w": 2.2}, {"gap": .3},
        {"id": "NUM4", "label": "4"}, {"id": "NUM5", "label": "5"}, {"id": "NUM6", "label": "6"},
    ],
    [
        {"id": "LSHIFT", "label": "Shift", "w": 2.45},
        *[{"id": c, "label": c} for c in "ZXCVBNM"],
        {"id": ",", "label": ","}, {"id": ".", "label": "."}, {"id": "/", "label": "/"},
        {"id": "RSHIFT", "label": "Shift", "w": 1.65}, {"id": "UP", "label": "↑"}, {"gap": .3},
        {"id": "NUM1", "label": "1"}, {"id": "NUM2", "label": "2"}, {"id": "NUM3", "label": "3"},
        {"id": "NUMENTER", "label": "Enter", "h": 2.1},
    ],
    [
        {"id": "LCTRL", "label": "Ctrl", "w": 1.35}, {"id": "FN", "label": "Fn"},
        {"id": "WIN", "label": "Win"}, {"id": "LALT", "label": "Alt"},
        {"id": "SPACE", "label": "Space", "w": 5.6},
        {"id": "RALT", "label": "Alt"}, {"id": "PRTSC", "label": "PrtSc"},
        {"id": "RCTRL", "label": "Ctrl", "w": 1.35}, {"gap": .65},
        {"id": "LEFT", "label": "←"}, {"id": "DOWN", "label": "↓"}, {"id": "RIGHT", "label": "→"},
        {"gap": .3}, {"id": "NUM0", "label": "0", "w": 2.0}, {"id": "NUMDEL", "label": "."},
    ],
]

GROUPS = {
    "wasd": ["W", "A", "S", "D"],
    "numbers": [str(i) for i in range(1, 10)] + ["0"],
    "functions": [f"F{i}" for i in range(1, 13)],
    "letters": list("QWERTYUIOPASDFGHJKLZXCVBNM"),
    "arrows": ["LEFT", "UP", "DOWN", "RIGHT"],
    "modifiers": ["LCTRL", "FN", "WIN", "LALT", "RALT", "RCTRL", "LSHIFT", "RSHIFT"],
    "numpad": [
        "NUMLOCK", "NUMDIV", "NUMMUL", "NUMMINUS",
        "NUM7", "NUM8", "NUM9", "NUMPLUS",
        "NUM4", "NUM5", "NUM6",
        "NUM1", "NUM2", "NUM3", "NUMENTER",
        "NUM0", "NUMDEL",
    ],
    "numpad_ops": [
        "NUMDIV", "NUMMUL", "NUMMINUS",
        "NUMPLUS", "NUMENTER", "NUMDEL",
    ],
}


def read_text(path: Path | str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def run_command(command: list[str], timeout: int = 5) -> tuple[int, str, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


def cpu_temperature() -> float | None:
    candidates, preferred = [], []
    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        if read_text(hwmon / "name") not in {"coretemp", "k10temp"}:
            continue
        for temp_input in hwmon.glob("temp*_input"):
            raw = read_text(temp_input)
            if raw is None:
                continue
            try:
                value = float(raw) / 1000.0
            except ValueError:
                continue
            label = read_text(temp_input.with_name(temp_input.name.replace("_input", "_label"))) or ""
            candidates.append(value)
            if "package" in label.lower() or "cpu" in label.lower():
                preferred.append(value)
    pool = preferred or candidates
    return round(max(pool), 1) if pool else None


def gpu_runtime_status() -> str:
    for dev in Path("/sys/bus/pci/devices").glob("*"):
        vendor = read_text(dev / "vendor")
        device_class = read_text(dev / "class")
        if vendor == "0x10de" and device_class and device_class.startswith("0x03"):
            return read_text(dev / "power/runtime_status") or "unknown"
    return "unknown"


def gpu_temperature() -> tuple[str, float | None]:
    state = gpu_runtime_status()
    if state != "active":
        return state, None
    code, output, _ = run_command([
        "/usr/bin/nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"
    ])
    if code == 0 and output:
        try:
            return state, float(output.splitlines()[0])
        except ValueError:
            pass
    return state, None


def asus_profile() -> tuple[str, str]:
    raw = read_text("/sys/firmware/acpi/platform_profile") or "unknown"
    names = {"quiet": "CICHY", "low-power": "CICHY", "balanced": "PERFORMANCE", "performance": "TURBO"}
    return raw, names.get(raw, raw.upper())


def service_status(service: str, user: bool = False) -> str:
    command = ["systemctl"] + (["--user"] if user else []) + ["is-active", service]
    _, output, _ = run_command(command)
    return output or "unknown"


def fan_speeds() -> dict[str, int | None]:
    result = {"cpu": None, "gpu": None, "mid": None}
    label_map = {"cpu_fan": "cpu", "gpu_fan": "gpu", "mid_fan": "mid"}
    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        if read_text(hwmon / "name") != "asus":
            continue
        for label_file in hwmon.glob("fan*_label"):
            key = label_map.get(read_text(label_file) or "")
            if not key:
                continue
            raw = read_text(label_file.with_name(label_file.name.replace("_label", "_input")))
            try:
                result[key] = int(raw) if raw is not None else None
            except ValueError:
                result[key] = None
    return result


def valid_packets(packets) -> bool:
    return (
        isinstance(packets, list)
        and len(packets) == 11
        and all(
            isinstance(row, list)
            and len(row) == 64
            and all(isinstance(value, int) and 0 <= value <= 255 for value in row)
            for row in packets
        )
    )


def load_packets(path: Path) -> list[list[int]] | None:
    try:
        packets = json.loads(path.read_text())
    except Exception:
        return None
    return packets if valid_packets(packets) else None


def valid_profile_id(profile_id: str | None) -> bool:
    return bool(PROFILE_ID_RE.fullmatch(profile_id or ""))


def read_profile(profile_id: str) -> dict | None:
    if not valid_profile_id(profile_id):
        return None
    directory = PROFILES_DIR / profile_id
    metadata_file = directory / "profile.json"
    packets_file = directory / "g834jz-rgb-base-packets.json"
    if not metadata_file.is_file() or load_packets(packets_file) is None:
        return None
    try:
        metadata = json.loads(metadata_file.read_text())
    except Exception:
        return None
    return {
        "id": profile_id,
        "name": str(metadata.get("name", profile_id)),
        "description": str(metadata.get("description", "")),
        "created": str(metadata.get("created", "")),
        "protected": profile_id in PROTECTED_IDS or bool(metadata.get("protected", False)),
        "directory": directory,
        "metadata_file": metadata_file,
        "packets": packets_file,
    }


def public_profile(profile: dict) -> dict:
    return {key: profile[key] for key in ("id", "name", "description", "created", "protected")}


def list_profiles() -> list[dict]:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for directory in sorted(PROFILES_DIR.iterdir()):
        if directory.is_dir():
            profile = read_profile(directory.name)
            if profile:
                result.append(public_profile(profile))
    return result


def read_state(path: Path, fallback: str) -> dict:
    try:
        data = json.loads(path.read_text())
        return {"id": data.get("id"), "name": data.get("name", fallback)}
    except Exception:
        return {"id": None, "name": fallback}


def active_profile() -> dict:
    return read_state(STATE_FILE, "Bieżący profil systemowy")


def default_profile() -> dict:
    return read_state(DEFAULT_FILE, "Nie ustawiono")


def atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=4))
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def regenerate_checksums(directory: Path) -> None:
    names = ["g834jz-rgb-profile.py", "g834jz-rgb-base-packets.json", "profile.json"]
    lines = []
    for name in names:
        path = directory / name
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {name}\n")
    (directory / "SHA256SUMS").write_text("".join(lines))


def save_state(path: Path, profile: dict) -> None:
    atomic_json(path, {"id": profile["id"], "name": profile["name"]})


def activate_profile(profile_id: str) -> dict:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje lub jest uszkodzony.")
    packets = load_packets(profile["packets"])
    if packets is None:
        raise ValueError("Profil ma nieprawidłową bazę RGB.")

    ACTIVE_BASE.parent.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    old_bytes = ACTIVE_BASE.read_bytes() if ACTIVE_BASE.is_file() else None
    if old_bytes is not None:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        backup = BACKUPS_DIR / stamp
        backup.mkdir(parents=True, exist_ok=True)
        (backup / ACTIVE_BASE.name).write_bytes(old_bytes)

    temporary = ACTIVE_BASE.with_name(ACTIVE_BASE.name + ".new")
    shutil.copy2(profile["packets"], temporary)
    if load_packets(temporary) is None:
        temporary.unlink(missing_ok=True)
        raise ValueError("Kopia profilu nie przeszła walidacji.")
    os.replace(temporary, ACTIVE_BASE)

    code, output, error = run_command(["systemctl", "--user", "restart", MONITOR_SERVICE], timeout=8)
    if code != 0:
        if old_bytes is not None:
            rollback = ACTIVE_BASE.with_name(ACTIVE_BASE.name + ".rollback")
            rollback.write_bytes(old_bytes)
            os.replace(rollback, ACTIVE_BASE)
            run_command(["systemctl", "--user", "restart", MONITOR_SERVICE], timeout=8)
        raise RuntimeError(error or output or "Nie udało się zrestartować monitora RGB.")

    save_state(STATE_FILE, profile)
    return profile


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "profil"


def next_profile_id(name: str) -> str:
    numbers = []
    for directory in PROFILES_DIR.glob("*"):
        match = re.match(r"^(\d+)-", directory.name)
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    slug = slugify(name)
    candidate = f"{number:02d}-{slug}"
    while (PROFILES_DIR / candidate).exists():
        number += 1
        candidate = f"{number:02d}-{slug}"
    return candidate


def create_profile(name: str, base_id: str) -> dict:
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        raise ValueError("Nazwa profilu musi mieć od 1 do 60 znaków.")
    base = read_profile(base_id)
    if not base:
        raise ValueError("Profil bazowy nie istnieje.")
    profile_id = next_profile_id(name)
    target = PROFILES_DIR / profile_id
    temp = PROFILES_DIR / f".{profile_id}.tmp"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)
    shutil.copy2(base["packets"], temp / "g834jz-rgb-base-packets.json")
    main_source = base["directory"] / "g834jz-rgb-profile.py"
    if main_source.is_file():
        shutil.copy2(main_source, temp / "g834jz-rgb-profile.py")
    atomic_json(temp / "profile.json", {
        "id": profile_id,
        "name": name,
        "description": f"Profil utworzony na podstawie: {base['name']}",
        "created": date.today().isoformat(),
        "protected": False,
    })
    regenerate_checksums(temp)
    os.replace(temp, target)
    return read_profile(profile_id)


def rename_profile(profile_id: str, name: str) -> dict:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    if profile["protected"]:
        raise PermissionError("Profil chroniony nie może być zmieniony.")
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        raise ValueError("Nazwa profilu musi mieć od 1 do 60 znaków.")
    metadata = json.loads(profile["metadata_file"].read_text())
    metadata["name"] = name
    atomic_json(profile["metadata_file"], metadata)
    regenerate_checksums(profile["directory"])
    if active_profile().get("id") == profile_id:
        atomic_json(STATE_FILE, {"id": profile_id, "name": name})
    if default_profile().get("id") == profile_id:
        atomic_json(DEFAULT_FILE, {"id": profile_id, "name": name})
    return read_profile(profile_id)


def delete_profile(profile_id: str) -> None:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    if profile["protected"]:
        raise PermissionError("Profil chroniony nie może być usunięty.")
    if active_profile().get("id") == profile_id:
        raise ValueError("Nie można usunąć aktywnego profilu.")
    if default_profile().get("id") == profile_id:
        raise ValueError("Nie można usunąć profilu domyślnego.")
    shutil.rmtree(profile["directory"])


def history_dirs(profile_id: str) -> tuple[Path, Path]:
    root = PROFILE_HISTORY_DIR / profile_id
    undo = root / "undo"
    redo = root / "redo"
    undo.mkdir(parents=True, exist_ok=True)
    redo.mkdir(parents=True, exist_ok=True)
    return undo, redo


def save_history_snapshot(profile: dict, clear_redo: bool = True) -> None:
    undo, redo = history_dirs(profile["id"])
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    shutil.copy2(profile["packets"], undo / f"{stamp}.json")
    if clear_redo:
        for file in redo.glob("*.json"):
            file.unlink(missing_ok=True)
    # Keep latest 50 undo snapshots.
    all_undo = sorted(undo.glob("*.json"))
    for old in all_undo[:-50]:
        old.unlink(missing_ok=True)


def restore_history(profile_id: str, direction: str) -> None:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    if profile["protected"]:
        raise PermissionError("Profil chroniony nie może być edytowany.")
    undo, redo = history_dirs(profile_id)
    source_dir, other_dir = (undo, redo) if direction == "undo" else (redo, undo)
    items = sorted(source_dir.glob("*.json"))
    if not items:
        raise ValueError("Brak zmian do cofnięcia." if direction == "undo" else "Brak zmian do ponowienia.")
    latest = items[-1]
    if load_packets(latest) is None:
        raise ValueError("Kopia historii jest uszkodzona.")
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    shutil.copy2(profile["packets"], other_dir / f"{stamp}.json")
    temporary = profile["packets"].with_name(profile["packets"].name + ".history")
    shutil.copy2(latest, temporary)
    os.replace(temporary, profile["packets"])
    latest.unlink(missing_ok=True)
    regenerate_checksums(profile["directory"])
    if active_profile().get("id") == profile_id:
        activate_profile(profile_id)


def key_colour(packets: list[list[int]], key_id: str) -> list[int] | None:
    slots = KEYMAP.get(key_id)
    if not slots:
        return None
    colours = [packets[p][o:o + 3] for p, o in slots]
    if not colours:
        return None
    # Multi-LED key: use first slot in UI; setting always writes all slots.
    return list(colours[0])


def keyboard_state(profile_id: str) -> dict:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    packets = load_packets(profile["packets"])
    if packets is None:
        raise ValueError("Profil ma nieprawidłową bazę RGB.")
    keys = {}
    for row in KEYBOARD_LAYOUT:
        for item in row:
            key_id = item.get("id")
            if not key_id:
                continue
            colour = key_colour(packets, key_id)
            keys[key_id] = {
                "rgb": colour,
                "hex": "#%02X%02X%02X" % tuple(colour) if colour else None,
                "mapped": colour is not None,
                "dynamic": key_id in DYNAMIC_KEYS,
                "editable": colour is not None and key_id not in DYNAMIC_KEYS and not profile["protected"],
            }
    return {
        "profile": public_profile(profile),
        "layout": KEYBOARD_LAYOUT,
        "groups": GROUPS,
        "keys": keys,
        "can_undo": bool(list(history_dirs(profile_id)[0].glob("*.json"))),
        "can_redo": bool(list(history_dirs(profile_id)[1].glob("*.json"))),
    }


def set_keys_colour(profile_id: str, key_ids: list[str], rgb: list[int]) -> list[str]:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    if profile["protected"]:
        raise PermissionError("FINAL i CODZIENNY są chronione przed edycją.")
    if not isinstance(key_ids, list) or not key_ids:
        raise ValueError("Nie wybrano żadnych klawiszy.")
    if not (isinstance(rgb, list) and len(rgb) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in rgb)):
        raise ValueError("Nieprawidłowy kolor RGB.")

    slots_by_key = {}
    for key_id in key_ids:
        slots = KEYMAP.get(key_id)
        if not slots:
            raise ValueError(f"Klawisz {key_id} nie ma bezpiecznego mapowania RGB.")
        if key_id in DYNAMIC_KEYS:
            raise PermissionError(f"Klawisz {key_id} jest sterowany dynamicznie.")
        slots_by_key[key_id] = slots

    packets = load_packets(profile["packets"])
    if packets is None:
        raise ValueError("Profil ma nieprawidłową bazę RGB.")
    changed = []
    for key_id, slots in slots_by_key.items():
        if any(packets[p][o:o + 3] != rgb for p, o in slots):
            changed.append(key_id)
    if not changed:
        return []

    save_history_snapshot(profile, clear_redo=True)
    for key_id in changed:
        for packet, offset in slots_by_key[key_id]:
            packets[packet][offset:offset + 3] = list(rgb)

    temporary = profile["packets"].with_name(profile["packets"].name + ".edit")
    temporary.write_text(json.dumps(packets))
    if load_packets(temporary) is None:
        temporary.unlink(missing_ok=True)
        raise ValueError("Zmodyfikowany profil nie przeszedł walidacji.")
    os.replace(temporary, profile["packets"])
    regenerate_checksums(profile["directory"])
    if active_profile().get("id") == profile_id:
        activate_profile(profile_id)
    return changed


def palette_for_profile(profile_id: str) -> list[dict]:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    packets = load_packets(profile["packets"])
    counts = Counter()
    used_slots = set()
    for key_id, slots in KEYMAP.items():
        if key_id in DYNAMIC_KEYS:
            continue
        for packet, offset in slots:
            if (packet, offset) in used_slots:
                continue
            used_slots.add((packet, offset))
            counts[tuple(packets[packet][offset:offset + 3])] += 1
    return [
        {"rgb": list(rgb), "hex": "#%02X%02X%02X" % rgb, "count": count}
        for rgb, count in counts.most_common()
    ]


def replace_palette_colour(profile_id: str, old_rgb: list[int], new_rgb: list[int]) -> int:
    profile = read_profile(profile_id)
    if not profile:
        raise ValueError("Profil nie istnieje.")
    if profile["protected"]:
        raise PermissionError("FINAL i CODZIENNY są chronione przed edycją.")
    valid_rgb = lambda value: isinstance(value, list) and len(value) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in value)
    if not valid_rgb(old_rgb) or not valid_rgb(new_rgb):
        raise ValueError("Nieprawidłowy kolor RGB.")
    packets = load_packets(profile["packets"])
    if packets is None:
        raise ValueError("Profil ma nieprawidłową bazę RGB.")

    slots = set()
    for key_id, key_slots in KEYMAP.items():
        if key_id in DYNAMIC_KEYS:
            continue
        slots.update(key_slots)
    targets = [(p, o) for p, o in slots if packets[p][o:o + 3] == old_rgb]
    if not targets:
        raise ValueError("Ten kolor nie występuje już w edytowalnej części profilu.")
    save_history_snapshot(profile, clear_redo=True)
    for packet, offset in targets:
        packets[packet][offset:offset + 3] = list(new_rgb)
    temporary = profile["packets"].with_name(profile["packets"].name + ".palette")
    temporary.write_text(json.dumps(packets))
    if load_packets(temporary) is None:
        temporary.unlink(missing_ok=True)
        raise ValueError("Zmodyfikowany profil nie przeszedł walidacji.")
    os.replace(temporary, profile["packets"])
    regenerate_checksums(profile["directory"])
    if active_profile().get("id") == profile_id:
        activate_profile(profile_id)
    return len(targets)


@app.get("/")
def index():
    return render_template("index.html", app_version=APP_VERSION)


@app.get("/editor/<profile_id>")
def editor(profile_id: str):
    profile = read_profile(profile_id)
    if not profile:
        return "Profil nie istnieje", 404
    if profile["protected"]:
        return "Profil jest chroniony", 403
    return render_template("editor.html", profile=public_profile(profile), app_version=APP_VERSION)


@app.get("/api/status")
def api_status():
    gpu_state, gpu_temp = gpu_temperature()
    raw_profile, profile_name = asus_profile()
    return jsonify({
        "ok": True,
        "cpu": cpu_temperature(),
        "gpu": {"state": gpu_state, "temperature": gpu_temp},
        "asus": {"raw": raw_profile, "name": profile_name},
        "services": {
            "rgb": service_status("g834jz-rgb-profile.service"),
            "monitor": service_status(MONITOR_SERVICE, user=True),
            "manager": service_status(MANAGER_SERVICE, user=True),
        },
        "fans": fan_speeds(),
        "rgb_profile": active_profile(),
        "default_profile": default_profile(),
    })


@app.post("/api/asus/next")
def api_asus_next():
    script = HOME / ".local/bin/rog-profile-next"
    code, output, error = run_command([str(script)], timeout=8)
    if code != 0:
        return jsonify(ok=False, error=error or output or "Błąd zmiany profilu ASUS."), 400
    raw, name = asus_profile()
    return jsonify(ok=True, asus={"raw": raw, "name": name})


@app.get("/api/profiles")
def api_profiles():
    return jsonify(ok=True, profiles=list_profiles(), active=active_profile(), default=default_profile())


@app.post("/api/profiles")
def api_create_profile():
    data = request.get_json(silent=True) or {}
    try:
        profile = create_profile(data.get("name", ""), data.get("base_id", "01-final"))
        return jsonify(ok=True, profile=public_profile(profile))
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/profiles/<profile_id>/activate")
def api_activate(profile_id: str):
    try:
        return jsonify(ok=True, profile=public_profile(activate_profile(profile_id)))
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/profiles/<profile_id>/default")
def api_default(profile_id: str):
    profile = read_profile(profile_id)
    if not profile:
        return jsonify(ok=False, error="Profil nie istnieje lub jest uszkodzony."), 400
    save_state(DEFAULT_FILE, profile)
    return jsonify(ok=True, profile=public_profile(profile))


@app.post("/api/profiles/<profile_id>/duplicate")
def api_duplicate(profile_id: str):
    source = read_profile(profile_id)
    if not source:
        return jsonify(ok=False, error="Profil nie istnieje."), 400
    data = request.get_json(silent=True) or {}
    try:
        profile = create_profile((data.get("name") or f"{source['name']} kopia").strip(), profile_id)
        return jsonify(ok=True, profile=public_profile(profile))
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/profiles/<profile_id>/rename")
def api_rename(profile_id: str):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(ok=True, profile=public_profile(rename_profile(profile_id, data.get("name", ""))))
    except PermissionError as exc:
        return jsonify(ok=False, error=str(exc)), 403
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.delete("/api/profiles/<profile_id>")
def api_delete(profile_id: str):
    try:
        delete_profile(profile_id)
        return jsonify(ok=True)
    except PermissionError as exc:
        return jsonify(ok=False, error=str(exc)), 403
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.get("/api/profiles/<profile_id>/keyboard")
def api_keyboard(profile_id: str):
    try:
        return jsonify(ok=True, **keyboard_state(profile_id), palette=palette_for_profile(profile_id))
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/profiles/<profile_id>/keys")
def api_keys(profile_id: str):
    data = request.get_json(silent=True) or {}
    try:
        changed = set_keys_colour(profile_id, data.get("keys"), data.get("rgb"))
        return jsonify(ok=True, changed=changed)
    except PermissionError as exc:
        return jsonify(ok=False, error=str(exc)), 403
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/profiles/<profile_id>/palette")
def api_palette(profile_id: str):
    data = request.get_json(silent=True) or {}
    try:
        changed = replace_palette_colour(profile_id, data.get("old"), data.get("new"))
        return jsonify(ok=True, changed=changed)
    except PermissionError as exc:
        return jsonify(ok=False, error=str(exc)), 403
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/profiles/<profile_id>/<direction>")
def api_history(profile_id: str, direction: str):
    if direction not in {"undo", "redo"}:
        return jsonify(ok=False, error="Nieprawidłowa operacja historii."), 404
    try:
        restore_history(profile_id, direction)
        return jsonify(ok=True)
    except PermissionError as exc:
        return jsonify(ok=False, error=str(exc)), 403
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


@app.get("/api/profiles/<profile_id>/export")
def api_export(profile_id: str):
    profile = read_profile(profile_id)
    if not profile:
        return jsonify(ok=False, error="Profil nie istnieje."), 404
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("profile.json", "g834jz-rgb-base-packets.json", "g834jz-rgb-profile.py", "SHA256SUMS"):
            path = profile["directory"] / name
            if path.is_file():
                archive.write(path, arcname=name)
    buffer.seek(0)
    filename = f"{profile_id}.zip"
    return send_file(buffer, mimetype="application/zip", as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False, threaded=True, use_reloader=False)
