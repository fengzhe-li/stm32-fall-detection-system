# Validation

This project has two distinct kinds of evidence. They are **not interchangeable**, and this page keeps them clearly separate.

## A. Historical Physical Validation (original project)

Recorded and photographed before the firmware hardening work in `docs/engineering-improvements.md` existed. This evidence shows the **original** build working, on the original hardware:

- Physical prototype assembled and operating (`docs/videos/physical-prototype.mp4`)
- OLED display operation, including the settings UI
- A physical fall/recovery cycle, with the corresponding OLED state change
- Buzzer alarm behavior
- SMS alerts received on a real phone (fall, SOS/help, heart rate, blood oxygen, temperature — see `docs/images/`)
- GPS location reporting, including a documented indoor-vs-outdoor comparison
- Health threshold configuration via the on-device keypad/OLED menu
- SOS button and cancel/acknowledge button operation
- A Proteus circuit simulation (`docs/videos/proteus-simulation.mp4`)

## B. Current Host-Side Verification (this reconstruction)

The firmware source in `firmware/` has since been through a source-level reconstruction and bug-fix pass. Each fix has a corresponding automated test that extracts the actual changed C functions and runs them on the host under Clang with **AddressSanitizer and UndefinedBehaviorSanitizer** (see `tests/`):

- Flash read/write bounds checking (byte/halfword unit correction)
- UART and GPS receive-buffer boundary handling (termination, overflow prevention)
- Malformed/truncated GPS sentence and SMS command handling
- GPS hemisphere sign correction (N/E positive, S/W negative)
- MAX30102 flat-signal divide-by-zero guard
- Cancel-button / fall-alarm suppression and re-arm state behavior
- Bounded GSM startup retry (finite attempts, explicit success/failure result)

These tests use hand-written hardware mocks and run entirely off-target; they demonstrate the absence of the specific defects they target, on the host.

## What Has *Not* Been Done Yet

**The hardened firmware has not yet been rebuilt with the target Keil/ARMCC toolchain, flashed to the STM32, or re-validated on the physical device after the reconstruction and bug-fix work.** Host-side sanitizer results are evidence that the fixed code paths behave correctly in isolation; they are not a substitute for a target rebuild and on-hardware retest, which remains outstanding.

In short: Section A shows the original device worked. Section B shows the specific defects found during reconstruction are fixed, in isolation, on the host. Neither currently stands in for the other.
