# STM32-Based Elderly Fall Detection and Health Monitoring System

A wearable safety device built on the **STM32F103C8T6**: it detects falls via accelerometer, monitors heart rate / SpO₂ / body temperature, and automatically sends an SMS alert with GPS location to a caregiver. Includes a manual SOS button, on-device threshold configuration, and remote SMS commands.

---

## 🎥 Physical Prototype Demonstration

▶️ **[Watch the physical prototype video](docs/videos/physical-prototype.mp4)**

![Device](docs/images/Photograph%20of%20the%20device.jpg)

The assembled hardware in operation — OLED display, sensors, GSM/GPS modules, keypad, and a physical fall/recovery cycle with the resulting alert behavior. This is historical evidence from the original build; see [Validation](#-validation) for what it does and does not confirm about the current firmware.

---

## 📌 Overview

The system integrates multiple sensors to monitor an elderly user's physiological state and motion in real time. On a fall or an abnormal vital sign, it sounds a local buzzer and sends an SMS alert containing current vitals and GPS coordinates. A short, fixed confirmation delay after a detected fall gives the wearer a chance to recover or cancel before the alert is sent.

## ⚙️ Features

- Fall detection with hysteresis (separate entry/recovery thresholds) and a fixed confirmation delay before alerting
- Automatic SMS alert on fall, abnormal heart rate, abnormal SpO₂, abnormal temperature, or manual SOS — each tracked independently
- GPS location embedded in every alert (hemisphere-aware coordinate sign)
- Cancel/acknowledge button that silences the buzzer and suppresses the current fall alert, without disabling future fall detection
- On-device OLED UI for live vitals, threshold configuration, and phone-number entry
- Remote SMS commands: request current data on demand, set the alert phone number remotely
- Persistent phone-number storage across power cycles (on-chip Flash)

## 🧩 Firmware & Architecture

Firmware source is available under [`firmware/`](firmware/) (`User/`, `Libraries/`, `Project/` — Keil MDK / ARM Compiler 5, ST Standard Peripheral Library, no HAL/RTOS).

Full architecture write-up — hardware modules, super-loop/interrupt structure, and the fall / health-alert / SOS-cancel flows — is in **[`docs/architecture.md`](docs/architecture.md)**.

## 🔧 Engineering Improvements

The recovered source underwent a memory-safety and control-logic hardening pass: Flash byte/halfword correction, UART/GPS receive-buffer protection, safer coordinate formatting, a GPS hemisphere-sign fix, a MAX30102 divide-by-zero guard, a cancel-alarm control-logic correction, and a bounded GSM startup retry.

Full write-up: **[`docs/engineering-improvements.md`](docs/engineering-improvements.md)**.

## ✅ Validation

Two distinct kinds of evidence exist for this project — **historical physical/simulation validation** of the original build, and **current host-side automated verification** (Clang + ASan/UBSan) of the hardening work above. They are kept clearly separate, and the hardened firmware has **not** yet been rebuilt in Keil, flashed, or re-validated on the physical device.

Full breakdown: **[`docs/validation.md`](docs/validation.md)**.

---

## 🧪 Experimental Results

| Working state | Fall & recovery | Heart-rate sensor active |
|---|---|---|
| ![Normal State](docs/images/Normal%20working%20state%20diagram.jpg) | ![Fall](docs/images/Real-life%20image%20of%20an%20elderly%20person%20falling%20and%20standing%20up.png) | ![Heart Sensor](docs/images/Red%20LED%20indicator%20when%20the%20heart%20rate%20sensor%20is%20active.jpg) |

**SMS alerts received:**

| Fall | SOS / help | Heart rate | Blood oxygen | Temperature |
|---|---|---|---|---|
| ![Fall SMS](docs/images/SMS%20received%20after%20the%20elderly%20person%20fall.png) | ![Help SMS](docs/images/SMS%20received%20after%20requesting%20help.jpg) | ![HR SMS](docs/images/Alert%20SMS%20received%20when%20the%20heart%20rate%20exceeds%20the%20threshold.jpg) | ![SpO2 SMS](docs/images/Alert%20SMS%20received%20when%20blood%20oxygen%20exceeds%20the%20threshold.jpg) | ![Temp SMS](docs/images/Alert%20SMS%20received%20when%20body%20temperature%20exceeds%20the%20threshold.jpg) |

**On-device threshold settings:**

| Heart rate | Blood oxygen | Body temperature | Phone number |
|---|---|---|---|
| ![HR threshold](docs/images/Heart%20rate%20threshold%20modification%20interface.jpg) | ![SpO2 threshold](docs/images/Blood%20oxygen%20threshold%20modification%20interface.jpg) | ![Temp threshold](docs/images/Body%20temperature%20threshold%20modification%20interface.jpg) | ![Phone setting](docs/images/SMS%20recipient%20phone%20number%20modification%20interface.jpg) |

## 📍 GPS Positioning Test

![GPS Test](docs/images/Figure%20X.%20Experimental%20results%20of%20the%20GPS%20module%20in%20indoor%20and%20open%20outdoor%20environments%20%28latitude%20and%20longitude%20can%20be%20clearly%20observed%20only%20in%20outdoor%20conditions%29.png)

Indoor environments cannot receive satellite signals, so latitude/longitude cannot be displayed indoors; in open outdoor environments, GPS coordinates are obtained normally.

## 🖥️ Proteus Simulation

▶️ **[Watch the Proteus simulation video](docs/videos/proteus-simulation.mp4)**  ·  ![Proteus](docs/images/Proteus%20simulation.png)

## 🔌 Circuit / Architecture References

| Circuit schematic | GSM & GPS display | SIM800 power supply |
|---|---|---|
| ![Circuit schematic](docs/images/Circuit%20schematic%20diagram.png) | ![GSM and GPS](docs/images/GSM%20and%20GPS%20Display%20Results.png) | ![SIM800 power](docs/images/SIM800%20external%20power%20supply%20diagram.jpg) |

---

## 📂 Repository Structure

```
stm32-fall-detection-system/
├── README.md
├── firmware/            # STM32 firmware source (User, Libraries, Project — Keil MDK)
├── hardware/            # Schematic / PCB design files (reference only, see notice below)
├── bom/                 # Bill of materials
├── docs/
│   ├── images/          # Photos, OLED/UI, and SMS alert screenshots
│   ├── videos/          # Physical prototype + Proteus simulation videos
│   ├── architecture.md
│   ├── validation.md
│   ├── engineering-improvements.md
│   └── U2180177 Li Fengzhe Final report.pdf
└── tests/               # Host-side verification scripts (Clang + ASan/UBSan)
```

## ⚠️ Hardware Files Notice

The `hardware/` folder contains schematic and PCB design files created during development. These represent design drafts and intermediate versions, and may not correspond exactly to the final hardware implementation used in the experiments. Provided for reference only.

## 📦 Bill of Materials

Component list: [`bom/list.xlsx`](bom/list.xlsx)

## 📄 Project Report

Full project dissertation: [`docs/U2180177 Li Fengzhe Final report.pdf`](docs/U2180177%20Li%20Fengzhe%20Final%20report.pdf)

## 👨‍💻 Author

**Fengzhe Li** — Embedded Systems | STM32 | IoT
