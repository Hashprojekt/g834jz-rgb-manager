#!/usr/bin/python3

import subprocess
import time
import glob
import os
import fcntl

# ============================================================
# ASUS ROG STRIX G834JZ — FINALNY PROFIL RGB
# ============================================================

TURQ   = (0, 80, 255)
ARROW  = (0, 254, 255)
RED    = (255, 0, 0)
ORANGE = (255, 90, 0)
YELLOW = (255, 190, 0)
BLUE   = (0, 80, 255)
GREEN  = (0, 255, 0)

BURGUNDY = (125, 90, 180)
VIOLET   = (140, 70, 180)
OLIVEGOLD = (110, 125, 25)
FULLYELLOW = (255, 255, 0)
SERVICE = "xyz.ljones.Asusd"
PATH    = "/xyz/ljones/aura/19b6_2_3"
IFACE   = "xyz.ljones.Aura"


# ============================================================
# Czekamy na asusd
# ============================================================

for _ in range(30):
    result = subprocess.run(
        ["busctl", "introspect", SERVICE, PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if result.returncode == 0:
        break

    time.sleep(0.5)
else:
    raise SystemExit("BŁĄD: ASUS Aura nie pojawiło się na D-Bus")


# ============================================================
# Aktywacja stref HID:
# 0 = Keyboard
# 1 = Lightbar
#
# Nowe kontrolery 19b6 potrafią wymagać tego przed Direct RGB.
# ============================================================

def hid_feature(report):
    report = bytes(report)
    length = len(report)

    # HIDIOCSFEATURE(length)
    ioctl_code = (
        (3 << 30) |
        (length << 16) |
        (ord('H') << 8) |
        0x06
    )

    for uevent in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        try:
            txt = open(uevent, "r").read().upper()
        except OSError:
            continue

        if "00000B05" not in txt or "000019B6" not in txt:
            continue

        dev = "/dev/" + uevent.split("/")[-3]

        try:
            fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)
            try:
                fcntl.ioctl(fd, ioctl_code, bytearray(report), True)
                return True
            finally:
                os.close(fd)
        except OSError:
            pass

    return False


# Keyboard ON w trybie Aura
hid_feature([0x5D, 0xC0, 0x00, 0x01, 0x01])

# Lightbar ON w trybie Aura
hid_feature([0x5D, 0xC0, 0x01, 0x01, 0x01])


# ============================================================
# 11 pakietów DirectAddressingRaw:
# 0-10 = wyłącznie klawiatura
#
# WAŻNE — POTWIERDZONE NA G834JZ 2026-08-26:
# Lightbar NIE może być tutaj wysyłany jako pakiet nr 11.
# Static ustawia kolor przedniej i bocznych listew,
# a DirectAddressingRaw nakłada później tylko profil klawiatury.
# Dzięki temu listwy pozostają zapalone.
# ============================================================

packets = []

for n in range(11):
    row = [0] * 64

    row[0] = 0x5d
    row[1] = 0xbc
    row[2] = 0x00
    row[3] = 0x01
    row[4] = 0x01
    row[5] = 0x01
    row[6] = n << 4

    # Końcowe grupy wymagają krótszej maski adresowania
    row[7] = 0x08 if n >= 10 else 0x10
    row[8] = 0x00

    # Cała klawiatura domyślnie turkusowa
    if n < 11:
        for col in range(9, 57, 3):
            row[col:col+3] = TURQ

    packets.append(row)


def key(packet, offset, colour):
    packets[packet][offset:offset+3] = colour


# ============================================================
# CZERWONE
# ============================================================

key(1, 24, RED)       # ESC

# TAB — kilka punktów, bo G834JZ nie zgadza się tu
# z generyczną mapą ASUS-a
key(3, 54, RED)
key(3, 57, RED)
key(3, 60, RED)

# WASD
key(4, 12, RED)       # W
key(5, 24, RED)       # A
key(5, 27, RED)       # S
key(5, 30, RED)       # D

# Backspace
for c in (30, 33, 36):
    key(3, c, RED)

# Backslash "\"
key(4, 45, RED)

# Główny Enter
for c in (9, 12, 15, 18):
    key(6, c, RED)

# Win
key(8, 9, RED)

# PrtSc — adres główny + dodatkowe wolne punkty
# wokół tego klawisza
key(8, 33, RED)
key(8, 39, RED)
key(8, 42, RED)


# ============================================================
# POMARAŃCZOWE
# ============================================================

key(0, 15, ORANGE)    # M1
key(0, 18, ORANGE)    # M2

# Spacja
for c in (15, 18, 21, 24, 27):
    key(8, c, ORANGE)


# ============================================================
# ŻÓŁTE
# Q + E
# ============================================================

key(4, 9, GREEN)
key(4, 15, GREEN)


# ============================================================
# ŻÓŁTE — NUMPAD
# NumLock + 0-9
# ============================================================

key(3, 42, YELLOW)    # NumLock

key(7, 39, YELLOW)    # 1
key(7, 42, YELLOW)    # 2
key(7, 45, YELLOW)    # 3

key(6, 24, YELLOW)    # 4
key(6, 27, YELLOW)    # 5
key(6, 30, YELLOW)    # 6

key(5, 9, YELLOW)     # 7
key(5, 12, YELLOW)    # 8
key(5, 15, YELLOW)    # 9

key(9, 9, YELLOW)     # 0


# ============================================================
# NIEBIESKIE — główny rząd 1-8
# ============================================================

for p, c in [
    (2,42), (2,45), (2,48), (2,51), (2,54),
    (3,9),  (3,12), (3,15)
]:
    key(p, c, BLUE)


# ============================================================
# NIEBIESKIE — STRZAŁKI
# ============================================================

key(7, 36, ARROW)      # ↑
key(8, 48, ARROW)      # ←
key(8, 51, ARROW)      # ↓
key(8, 54, ARROW)      # →


# ============================================================
# Delete / Insert nad NumPadem -> pomarańczowy
key(2, 27, ORANGE)    # Delete

# ZIELONE — F4 + F8 + F12
# ============================================================

key(1, 39, (170, 40, 230))
key(1, 54, (170, 40, 230))
key(2, 21, (170, 40, 230))


# ============================================================
# LIGHTBAR — UWAGA IMPLEMENTACYJNA
#
# NIE wpisujemy Lightbara do tablicy `packets`.
#
# Wcześniejszy wariant:
#   pakiet nr 11 + key(11, ...)
#
# powodował wygaszenie przedniej i bocznych listew.
#
# Działający wariant:
#   1. aura power lightbar
#   2. aura effect static
#   3. DirectAddressingRaw tylko dla 11 pakietów klawiatury
# ============================================================


# ============================================================
# Stany zasilania
# ============================================================

# Logo OFF
subprocess.run(
    ["asusctl", "aura", "power", "logo"],
    check=True
)

# Tylna listwa OFF
subprocess.run(
    ["asusctl", "aura", "power", "rear-glow"],
    check=True
)

# Przód + boki ON
subprocess.run(
    [
        "asusctl", "aura", "power", "lightbar",
        "--boot", "--awake", "--sleep", "--shutdown"
    ],
    check=True
)


# ============================================================
# Wysłanie danych RGB
# ============================================================


# Główny rząd cyfr 1-8 -> średni, spokojny fiolet
for p_, c_ in (
    (2,42), (2,45), (2,48), (2,51),
    (2,54), (3,9), (3,12), (3,15)
):
    key(p_, c_, (255, 255, 0))


# ============================================================
# FINAL: G834JZ
# ============================================================

# Główna klawiatura: 9 i 0 -> FIOLET
key(3, 18, VIOLET)     # 9
key(3, 21, VIOLET)     # 0


# ------------------------------------------------------------
# LIGHTBAR
#
# Ta kolejność została POTWIERDZONA na tym G834JZ:
# Static budzi przednią/boczną listwę,
# następnie DirectAddressingRaw przywraca profil klawiatury,
# a listwa pozostaje zapalona.
# ------------------------------------------------------------

subprocess.run([
    "asusctl", "aura", "power", "lightbar",
    "--boot", "--awake", "--sleep", "--shutdown"
], check=True)

subprocess.run(
    ["asusctl", "aura", "power", "logo"],
    check=True
)

subprocess.run(
    ["asusctl", "aura", "power", "rear-glow"],
    check=True
)

# Dokładnie ten efekt uruchomił działającą listwę
subprocess.run([
    "asusctl", "aura", "effect", "static",
    "-c", "0050ff"
], check=True)

# Krótki czas na zastosowanie Static przed Per-Key
time.sleep(1)


# FINALNE NADPISANIA KOLORÓW

# Główne 9 i 0 -> oliwkowo-złote
key(3, 18, ORANGE)    # 9
key(3, 21, ORANGE)    # 0
key(3, 24, GREEN)     # -
key(3, 27, GREEN)     # =

# Spacja -> maksymalnie jasny żółty
for c_ in (15, 18, 21, 24, 27):
    key(8, c_, FULLYELLOW)


# ============================================================
# HOME — WSKAŹNIK PROFILU WYDAJNOŚCI
#
# ASUS G834JZ:
# HOME = LED 41 = packet 2 / offset 36
#
# Quiet       -> zielony
# Balanced    -> pomarańczowy
# Performance -> czerwony
#
# Wcześniejsze nazewnictwo użytkowe:
# Quiet       ~ tryb cichy
# Balanced    ~ tryb optymalny
# Performance ~ najwyższy profil wydajności asusctl
# ============================================================

try:
    _platform_profile = open(
        "/sys/firmware/acpi/platform_profile",
        "r"
    ).read().strip().lower()
except OSError:
    _platform_profile = "balanced"

_HOME_COLOUR = {
    "quiet":       GREEN,
    "low-power":   GREEN,
    "balanced":    ORANGE,
    "performance": RED,
}.get(_platform_profile, ORANGE)

key(2, 36, _HOME_COLOUR)    # HOME / LED 41
key(0, 24, _HOME_COLOUR)    # M4 / LED 5 / FAN key

cmd = [
    "busctl", "call",
    SERVICE,
    PATH,
    IFACE,
    "DirectAddressingRaw",
    "aay",
    str(len(packets))
]

for row in packets:
    cmd.append(str(len(row)))
    cmd.extend(str(x) for x in row)

subprocess.run(cmd, check=True)


# Ponowna aktywacja Lightbar po przełączeniu w Direct RGB
hid_feature([0x5D, 0xC0, 0x01, 0x01, 0x01])

# Ponownie wymuszamy pożądane strefy
subprocess.run(["asusctl", "aura", "power", "logo"], check=True)
subprocess.run(["asusctl", "aura", "power", "rear-glow"], check=True)
subprocess.run(
    [
        "asusctl", "aura", "power", "lightbar",
        "--boot", "--awake", "--sleep", "--shutdown"
    ],
    check=True
)

print("OK: profil RGB G834JZ zastosowany.")
