#!/usr/bin/python3

import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# ASUS ROG STRIX G834JZ
#
# M3 = RTX 4080
# M4 = profil CICHY / PERFORMANCE / TURBO
# M5 = CPU
#
# WAŻNE:
# wysyłamy zawsze pełne 11 pakietów klawiatury.
# Nigdy samotnego packet 0.
# ============================================================

SERVICE = "xyz.ljones.Asusd"
DBUS_PATH = "/xyz/ljones/aura/19b6_2_3"
IFACE = "xyz.ljones.Aura"

BASE_FILE = Path.home() / ".config/g834jz-rgb-base-packets.json"


# ============================================================
# KOLORY
# ============================================================

BLUE        = (0, 80, 255)
SLEEP_BLUE  = (0, 20, 80)
GPU_UNKNOWN = (170, 0, 255)

GREEN  = (0, 255, 0)
YELLOW = (255, 160, 0)
ORANGE = (255, 80, 0)
RED    = (255, 0, 0)
OFF    = (0, 0, 0)


# ============================================================
# WCZYTANIE PEŁNEJ KOLOROWANKI
# ============================================================

try:
    packets = json.loads(BASE_FILE.read_text())
except Exception as exc:
    raise SystemExit(
        f"BŁĄD: nie można wczytać {BASE_FILE}: {exc}"
    )

if len(packets) != 11:
    raise SystemExit(
        f"BŁĄD: baza RGB ma {len(packets)} pakietów zamiast 11."
    )

for nr, row in enumerate(packets):
    if len(row) != 64:
        raise SystemExit(
            f"BŁĄD: packet {nr} ma {len(row)} bajtów zamiast 64."
        )


def read_text(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def read_millidegrees(path):
    value = read_text(path)

    if value is None:
        return None

    try:
        value = float(value)
    except ValueError:
        return None

    if value > 1000:
        value /= 1000.0

    return value


# ============================================================
# CPU
# ============================================================

def cpu_temperature():
    fallback = []

    for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        name = (read_text(os.path.join(hwmon, "name")) or "").lower()

        if name not in ("coretemp", "k10temp"):
            continue

        for input_path in glob.glob(
            os.path.join(hwmon, "temp*_input")
        ):
            base = input_path[:-6]
            label = (read_text(base + "_label") or "").lower()
            temp = read_millidegrees(input_path)

            if temp is None:
                continue

            if (
                "package id 0" in label
                or label in ("package", "cpu")
            ):
                return temp

            fallback.append(temp)

    return max(fallback) if fallback else None


# ============================================================
# RTX — RUNTIME STATUS
# ============================================================

def gpu_runtime_status():
    for device in glob.glob("/sys/bus/pci/devices/*"):
        vendor = (
            read_text(os.path.join(device, "vendor")) or ""
        ).lower()

        pci_class = (
            read_text(os.path.join(device, "class")) or ""
        ).lower()

        if vendor != "0x10de":
            continue

        if not pci_class.startswith("0x03"):
            continue

        return (
            read_text(
                os.path.join(
                    device,
                    "power",
                    "runtime_status"
                )
            )
            or "unknown"
        ).lower()

    return "unknown"


# ============================================================
# RTX — TEMPERATURA
# ============================================================

def gpu_temperature():
    # Nie uruchamiamy nvidia-smi, jeżeli RTX naprawdę śpi.
    if gpu_runtime_status() != "active":
        return None

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=True,
        )

        value = result.stdout.strip().splitlines()[0]
        return float(value)

    except (
        subprocess.SubprocessError,
        OSError,
        ValueError,
        IndexError,
    ):
        return None


# ============================================================
# CPU -> KOLOR
# ============================================================

def cpu_temperature_colour(temp, blink):
    # <= 69°C  zielony
    # 70-79°C  żółty
    # 80-89°C  pomarańczowy
    # 90-96°C  czerwony
    # >= 97°C  migający czerwony

    if temp is None:
        return BLUE

    if temp < 70:
        return GREEN

    if temp < 80:
        return YELLOW

    if temp < 90:
        return ORANGE

    if temp < 97:
        return RED

    return RED if blink else OFF


# ============================================================
# RTX -> KOLOR
# ============================================================

def gpu_temperature_colour(temp, state, blink):
    # suspended  niebieski
    # active bez temperatury  fioletowy
    #
    # < 65°C   zielony
    # 65-74°C  żółty
    # 75-81°C  pomarańczowy
    # 82-86°C  czerwony
    # >=87°C   migający czerwony

    if state == "suspended":
        return SLEEP_BLUE

    if temp is None:
        return GPU_UNKNOWN

    if temp < 65:
        return GREEN

    if temp < 75:
        return YELLOW

    if temp < 82:
        return ORANGE

    if temp < 87:
        return RED

    return RED if blink else OFF


# ============================================================
# PROFIL ASUS -> KOLOR
# ============================================================

def profile_colour():
    profile = (
        read_text("/sys/firmware/acpi/platform_profile")
        or "balanced"
    ).lower()

    if profile in ("quiet", "low-power"):
        return GREEN

    if profile == "balanced":
        return ORANGE

    if profile == "performance":
        return RED

    return ORANGE


# ============================================================
# PEŁNE 11 PAKIETÓW
# ============================================================

def send_packets():
    cmd = [
        "busctl",
        "call",
        SERVICE,
        DBUS_PATH,
        IFACE,
        "DirectAddressingRaw",
        "aay",
        str(len(packets)),
    ]

    for row in packets:
        cmd.append(str(len(row)))
        cmd.extend(str(x) for x in row)

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


# ============================================================
# CZEKAMY NA ASUS AURA
# ============================================================

for _ in range(30):
    result = subprocess.run(
        [
            "busctl",
            "introspect",
            SERVICE,
            DBUS_PATH,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode == 0:
        break

    time.sleep(0.5)

else:
    raise SystemExit(
        "BŁĄD: ASUS Aura nie pojawiło się na D-Bus."
    )


# ============================================================
# STABILIZACJA TEMPERATURY
# ============================================================

cpu_hold_temp = None
gpu_hold_temp = None

cpu_hold_until = 0.0
gpu_hold_until = 0.0

HOLD_SECONDS = 10.0

blink = True

once = "--once" in sys.argv


# ============================================================
# PĘTLA
# ============================================================

while True:
    now = time.monotonic()

    cpu = cpu_temperature()

    gpu_state = gpu_runtime_status()
    gpu = gpu_temperature() if gpu_state == "active" else None


    # --------------------------------------------------------
    # CPU — zapamiętujemy chwilowy wyższy skok przez 10 sekund
    # --------------------------------------------------------

    if cpu is not None:
        if cpu_hold_temp is None or cpu >= cpu_hold_temp:
            cpu_hold_temp = cpu
            cpu_hold_until = now + HOLD_SECONDS

        elif now >= cpu_hold_until:
            cpu_hold_temp = cpu
            cpu_hold_until = now + HOLD_SECONDS


    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    if gpu_state == "suspended":
        gpu_hold_temp = None
        gpu_hold_until = 0.0

    elif gpu is not None:
        if gpu_hold_temp is None or gpu >= gpu_hold_temp:
            gpu_hold_temp = gpu
            gpu_hold_until = now + HOLD_SECONDS

        elif now >= gpu_hold_until:
            gpu_hold_temp = gpu
            gpu_hold_until = now + HOLD_SECONDS


    cpu_display = (
        cpu_hold_temp
        if cpu_hold_temp is not None
        else cpu
    )

    gpu_display = (
        gpu_hold_temp
        if gpu_hold_temp is not None
        else gpu
    )


    # ========================================================
    # NADPISUJEMY TYLKO WSKAŹNIKI
    #
    # M3   LED 4  -> packet 0 / offset 21
    # M4   LED 5  -> packet 0 / offset 24
    # M5   LED 6  -> packet 0 / offset 27
    #
    # HOME LED 41 -> packet 2 / offset 36
    # ========================================================

    packets[0][21:24] = gpu_temperature_colour(
        gpu_display,
        gpu_state,
        blink,
    )

    profile = profile_colour()

    packets[0][24:27] = profile     # M4
    packets[2][36:39] = profile     # HOME

    packets[0][27:30] = cpu_temperature_colour(
        cpu_display,
        blink,
    )


    # Wysyłamy CAŁĄ klawiaturę — 11 pakietów.
    send_packets()


    if once:
        print(
            "CPU:",
            "brak" if cpu is None else f"{cpu:.1f}°C"
        )

        print(
            "RTX:",
            gpu_state,
            "/" if gpu is not None else "",
            "" if gpu is None else f"{gpu:.1f}°C"
        )

        break


    # Dotychczasowa częstotliwość migania pozostaje bez zmian.
    blink = not blink

    time.sleep(1)
