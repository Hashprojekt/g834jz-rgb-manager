# G834JZ RGB Manager

**🇵🇱 [Polski](#-polski) | 🇬🇧 [English](#-english)**

Local RGB, hardware monitoring and ASUS performance profile manager for the
**ASUS ROG Strix G834JZ**, designed primarily for Linux / Nobara.

> [!IMPORTANT]
> This project is currently developed and tested on an ASUS ROG Strix G834JZ.
> RGB packet layouts may differ on other ASUS laptops.

---

# 🇵🇱 Polski

## O projekcie

**G834JZ RGB Manager** to lokalna aplikacja WWW do zarządzania podświetleniem RGB
oraz monitorowania wybranych parametrów laptopa **ASUS ROG Strix G834JZ**
pod Linuksem.

Projekt powstał jako alternatywa dla części funkcji dostępnych w Armoury Crate / Aura
na Windowsie.

Panel działa lokalnie pod adresem:

```text
http://127.0.0.1:8765
```

## ✨ Funkcje

- profile RGB,
- tworzenie, duplikowanie, zmiana nazwy i usuwanie profili użytkownika,
- profile chronione `FINAL` i `CODZIENNY`,
- wizualny edytor klawiatury per-key,
- wybór pojedynczych klawiszy i grup,
- wybór kolorów HEX / RGB,
- cofanie i ponawianie zmian,
- edycja wielopunktowego klawisza Space,
- obsługa NumLock, numpada 0–9 oraz operatorów `/`, `*`, `-`, `+`, `Enter`, `.`,
- odczyt temperatur CPU i GPU,
- odczyt RPM trzech wentylatorów,
- przełączanie profili ASUS,
- integracja z GameMode,
- dynamiczne wskaźniki M3 / M4 / M5.

## 🌡️ Monitoring sprzętu

Panel pokazuje na żywo:

- temperaturę CPU,
- temperaturę NVIDIA RTX 4080 Laptop GPU,
- stan GPU,
- CPU FAN,
- GPU FAN,
- MID FAN.

## 💡 M3 / M4 / M5

### M3 — GPU

Kolor klawisza informuje o stanie i temperaturze GPU.

### M4 — profil ASUS

- 🟢 CICHY
- 🟠 PERFORMANCE
- 🔴 TURBO

### M5 — CPU

Kolor klawisza zmienia się wraz z temperaturą procesora.

## 🌈 Lightbar

Konfiguracja testowana na G834JZ:

- front + sides: ON,
- Rear Glow: OFF,
- Logo: OFF,
- 11 pakietów DirectAddressingRaw.

> [!WARNING]
> Na testowanym G834JZ wysłanie 12. pakietu powodowało wyłączenie części Lightbara.
> Projekt nie powinien wysyłać 12. pakietu.

## 📦 Wymagania

Projekt jest rozwijany na:

- ASUS ROG Strix G834JZ,
- Nobara Linux 44,
- KDE Plasma / Wayland,
- Python 3,
- Flask,
- `asusctl`,
- `asusd`,
- NVIDIA proprietary driver,
- systemd.

Instalacja zależności Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Uruchomienie developerskie:

```bash
source .venv/bin/activate
python app.py
```

Następnie otwórz:

```text
http://127.0.0.1:8765
```

## 🔒 Bezpieczeństwo

Aplikacja domyślnie nasłuchuje wyłącznie na `127.0.0.1`.
Nie jest przeznaczona do bezpośredniego wystawiania do Internetu.

## ⚠️ Zgodność sprzętowa

Projekt jest tworzony i testowany na **ASUS ROG Strix G834JZ**.
Nie należy zakładać zgodności mapowania LED z innymi modelami ASUS.

## 🚧 Status

Aktualna wersja: **v1.3**

---

# 🇬🇧 English

## About

**G834JZ RGB Manager** is a local web application for controlling RGB lighting
and monitoring selected hardware parameters on the **ASUS ROG Strix G834JZ**
running Linux.

It was created as a Linux alternative for part of the functionality normally
provided by Armoury Crate / Aura on Windows.

The dashboard runs locally at:

```text
http://127.0.0.1:8765
```

## ✨ Features

- multiple RGB profiles,
- create, duplicate, rename and delete user profiles,
- protected `FINAL` and `CODZIENNY` profiles,
- visual per-key keyboard editor,
- single-key and multi-key selection,
- predefined key groups,
- HEX / RGB colour selection,
- undo / redo,
- multi-zone Space key support,
- NumLock, numpad digits 0–9 and operators `/`, `*`, `-`, `+`, `Enter`, `.`,
- CPU and GPU temperature monitoring,
- three-fan RPM monitoring,
- ASUS performance profile switching,
- GameMode integration,
- dynamic M3 / M4 / M5 indicators.

## 🌡️ Hardware monitoring

The dashboard shows:

- CPU temperature,
- NVIDIA RTX 4080 Laptop GPU temperature,
- GPU runtime state,
- CPU fan RPM,
- GPU fan RPM,
- middle fan RPM.

## 💡 M3 / M4 / M5

### M3 — GPU

The key colour represents GPU state and temperature.

### M4 — ASUS performance profile

- 🟢 SILENT
- 🟠 PERFORMANCE
- 🔴 TURBO

### M5 — CPU

The key colour changes according to CPU temperature.

## 🌈 Lightbar

Configuration tested on the G834JZ:

- front + sides: ON,
- Rear Glow: OFF,
- Logo: OFF,
- 11 DirectAddressingRaw packets.

> [!WARNING]
> On the tested G834JZ, sending a 12th packet caused part of the Lightbar to turn off.
> The project should not send a 12th packet.

## 📦 Requirements

The project is currently developed on:

- ASUS ROG Strix G834JZ,
- Nobara Linux 44,
- KDE Plasma / Wayland,
- Python 3,
- Flask,
- `asusctl`,
- `asusd`,
- proprietary NVIDIA driver,
- systemd.

Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Development run:

```bash
source .venv/bin/activate
python app.py
```

Then open:

```text
http://127.0.0.1:8765
```

## 🔒 Security

By default the application listens only on `127.0.0.1`.
It is not intended to be exposed directly to the Internet.

## ⚠️ Hardware compatibility

This project is developed and tested on the **ASUS ROG Strix G834JZ**.
Do not assume that its LED mapping is compatible with other ASUS models.

## 🚧 Status

Current version: **v1.3**

---

## License

A license file will be added before the first public release.
