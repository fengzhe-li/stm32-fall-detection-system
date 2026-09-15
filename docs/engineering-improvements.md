# Engineering Improvements

The original recovered firmware source contained a number of memory-safety and control-logic defects, typical of a student embedded project written without static analysis, sanitizers, or an automated test suite. This document summarizes the hardening work performed on it. All fixes preserve the original fall-detection thresholds, alarm timing, and outgoing SMS wording except where explicitly noted; each is covered by a host-side automated test under `tests/`.

## Memory / Bounds Safety

- **Flash byte/halfword correction:** the on-chip Flash read/write helpers and their callers mixed byte and halfword units, causing over-reads/over-writes beyond the intended storage objects (phone number, magic marker). Corrected to consistent, explicitly-sized halfword access with full bounds validation (non-zero length, alignment, in-range address) before any Flash access.
- **UART/GPS receive protection:** the USART1 and USART3 receive-buffer handlers could fill without guaranteed NUL-termination and, for GPS, without an upper bound on frame length. Both now reserve terminator space, discard/guard oversized input, and recover cleanly on the next valid frame.
- **Safer coordinate formatting:** fixed-size coordinate buffers were sized for only the nominal case; unusual or extreme floating-point values could overflow them. Formatting now uses explicit size-bounded `snprintf` throughout.
- **Sensor buffer initialization:** a sensor sample buffer was read one index past its last valid element during startup initialization; corrected to read the last valid sample.
- **GPS field parsing:** numeric field extraction now validates delimiter positions and field lengths before copying, eliminating an unsigned-underflow path that could occur on malformed or truncated NMEA sentences.

## Correctness Fixes

- **GPS hemisphere correction:** the parsed hemisphere indicator (N/S/E/W) was read but never applied to the computed latitude/longitude, so southern and western coordinates were reported with the wrong (positive) sign. Now applied: N/E stay positive, S/W are negated.
- **MAX30102 numeric guard:** a brightness-normalization calculation divided by the sensor's observed signal range without checking for a flat (no-signal) reading, which could divide by zero. Guarded to skip the update on a flat reading rather than compute an undefined result.
- **Cancel-alarm control-logic correction:** the button intended to suppress a pending fall alert checked the *recovery* condition instead of the *currently-fallen* condition — a leftover from an earlier hardware revision that used inverted thresholds. As a result, pressing cancel during an active fall could not stop the pending alert, while pressing it while merely standing could incorrectly pre-suppress a future, unrelated fall. Corrected to check the actual current-fall state, so cancel now reliably suppresses only the pending alert for the fall in progress, without disabling later fall alerts.
- **English outgoing phone-number setup messages:** the two outgoing SMS replies for a remote phone-number-change request were translated to English, matching the rest of the outgoing message set (incoming command matching is unchanged, for protocol compatibility).

## Reliability

- **Bounded GSM startup retry:** modem initialization previously retried an unanswered AT command indefinitely, which could hang the entire firmware at boot if the modem never responded. Initialization now retries a finite number of times per command and returns an explicit success/failure result, so the rest of the system starts even if the modem never answers.

## Verification

Every item above has a corresponding host-side test in `tests/` that extracts the actual fixed C function(s) and exercises the specific boundary condition under Clang with AddressSanitizer/UndefinedBehaviorSanitizer. See `docs/validation.md` for what this does and does not establish.
