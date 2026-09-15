# System Architecture

## Hardware

| Module | Component | Interface | Role |
|---|---|---|---|
| MCU | STM32F103C8T6 (ARM Cortex-M3) | — | Main controller, register-level firmware via the ST Standard Peripheral Library (no HAL, no RTOS) |
| Accelerometer | ADXL345 | I²C (bit-banged) | Fall detection input |
| Pulse oximeter | MAX30102 | I²C | Heart rate & SpO₂ (photoplethysmography) |
| Temperature sensor | DS18B20 | 1-Wire | Body temperature |
| Display | 128×64 OLED (SSD1306-family) | I²C | Live vitals, settings UI |
| Cellular modem | SIM800C | USART1, AT commands, UCS2 SMS text mode | Outgoing alerts, incoming remote commands |
| GPS receiver | NMEA-output GPS module | USART3 | Location (`$GPRMC` sentences) |
| Buzzer | Piezo buzzer | GPIO | Local audible alert |
| Input | 5-button keypad | GPIO (polled) | SOS / cancel / settings navigation |
| Storage | Internal Flash sector | — | Persistent phone-number storage |

## Firmware Structure

The firmware is a bare-metal, single `main()` super-loop — there is no RTOS and no task scheduler. Each loop iteration polls sensors, evaluates alarms, handles key input, and refreshes the display in sequence.

Two peripherals run asynchronously alongside the main loop via interrupt-fed receive buffers:

- **USART1 (GSM/SMS):** `USART1_IRQHandler` fills a receive buffer byte-by-byte and detects the modem's `OK` response inline; the main loop parses buffered AT responses and incoming SMS text once per iteration.
- **USART3 (GPS):** `USART3_IRQHandler` accumulates one NMEA sentence per interrupt-driven pass; the main loop parses a completed `$GPRMC` sentence once per iteration.

All application logic lives in `firmware/User/main.c`, with one driver file per peripheral (`adxl345.c`, `max30102.c`, `ds18b20.c`, `GPS.c`, `usart1.c`, `usart3.c`, `stmflash.c`, `OLED_I2C.c`, `key.c`).

## Fall → Confirmation → Buzzer/SMS Flow

1. `FallDetection()` averages 10 accelerometer X-axis samples per call. Crossing above a fixed fall-entry threshold latches a "fallen" state (`FALL !` on the OLED); dropping below a separate, lower recovery threshold clears it (`STAND`) and sends a recovery SMS unless acknowledged. The two different thresholds (rather than one) implement hysteresis, preventing rapid state toggling at a single boundary.
2. While latched, a fixed, non-configurable countdown runs before an alert is sent — this gives the wearer a window to recover or cancel before an alert goes out. (The countdown length is a source-level constant, not exposed as a user setting.)
3. If the countdown elapses without recovery, the buzzer sounds and an SMS is sent containing the event type, current vitals, and last-known GPS coordinates.
4. A dedicated cancel button silences the buzzer immediately and suppresses the pending alert for the *current* fall event only — it does not disable fall detection going forward; a later, independent fall event still alerts normally once the wearer has recovered from the current one.

## Health Abnormality Alert Flow

- Heart rate and SpO₂ are derived from the MAX30102 signal, smoothed with a moving average and simple outlier rejection.
- Body temperature is read from the DS18B20 each cycle.
- Each vital (heart rate, SpO₂, temperature) has its own configurable min/max threshold, adjustable on-device via the keypad and OLED settings menu.
- Each vital tracks its own independent alarm state: crossing a threshold triggers that vital's own SMS alert, and recovering from one abnormal vital does not silence an unrelated one that's still active.

## SOS / Cancel Behavior

- A dedicated SOS button triggers the same alert pipeline as a fall or health event, tracked with its own independent alarm-state bit so it doesn't interfere with — or get suppressed by — fall or health alarms.
- The cancel button immediately silences the buzzer and clears the SOS alarm state, and (as described above) suppresses only the currently pending fall alert without disabling future detection.

## Remote Communication

- **GPS:** `$GPRMC` sentences are parsed into latitude/longitude, converted from degrees-minutes to decimal degrees, and sign-corrected for the reported hemisphere (N/E positive, S/W negative).
- **GSM/SMS:** the modem is initialized over USART1 with a fixed AT-command sequence and communicates in UCS2-encoded SMS text mode. Outgoing alerts embed vitals and location; the device also accepts two incoming SMS commands — request current data on demand, and remotely set the alert phone number.
