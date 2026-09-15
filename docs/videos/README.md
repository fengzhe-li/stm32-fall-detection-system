# Project Videos

This folder contains the two historical demonstration videos from the original final-year project, prepared as GitHub-friendly copies of the original source recordings.

## Files

### `physical-prototype.mp4`
**Historical physical prototype demonstration — primary hardware evidence.**

Shows the assembled STM32 hardware in operation: the STM32F103 board, OLED display, GPS/GSM modules, accelerometer, heart-rate sensor, and keypad, including a physical fall/recovery cycle and the resulting OLED and alert behavior.

- Prepared from the original ~248 MB source (1080×1920, H.264, ~17 Mbps) by re-encoding to 540×960 H.264 (same 9:16 aspect ratio, same ~122 s duration, no trimming) to fit GitHub's file-size limits while keeping the OLED text and hardware labels readable.
- The original, full-resolution source file is preserved unmodified outside this repository and was not altered by this process.

### `proteus-simulation.mp4`
**Historical Proteus simulation demonstration — secondary supporting evidence.**

Shows the circuit simulated in Proteus. Copied as-is from the original source (already H.264 MP4, ~4.9 MB) with no re-encoding, since it was already suitable for GitHub.

## What these videos do — and do not — demonstrate

Both videos document the **original** project's physical prototype and simulation behavior, recorded before the source-code reconstruction and bug-fix work in this repository.

- They are historical evidence of the original device/simulation working as built at the time.
- They are **not** a demonstration of the current, hardened firmware in this repository. The current firmware has undergone a separate reconstruction and bug-fix effort (see `RECONSTRUCTION_CHANGELOG.md` and the `BUGFIX_ROUND_*` reports/verification scripts), covering memory/bounds fixes, UART/GPS input handling, GPS hemisphere sign correction, a flat-signal divide-by-zero guard, a cancel-alarm logic fix, and a bounded GSM startup retry.
- That hardening work has been verified with host-side automated tests (Clang + AddressSanitizer/UndefinedBehaviorSanitizer) exercising the specific fixed code paths — it has **not** yet been rebuilt with the target Keil/ARMCC toolchain, flashed to hardware, or re-validated on the physical device.

In short: these videos show the original project worked; the host-side tests show the specific defects found during reconstruction are fixed in isolation. Neither one currently substitutes for the other, and a target rebuild/re-flash to confirm the hardened firmware on real hardware remains outstanding.
