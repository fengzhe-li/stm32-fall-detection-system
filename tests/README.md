# Host-Side Verification Tests

These are **host-side regression/verification scripts** for the specific defects fixed during the firmware hardening pass (see [`docs/engineering-improvements.md`](../docs/engineering-improvements.md)). Each script extracts the actual, current C functions from [`firmware/User/`](../firmware/User/), compiles them on your machine with Clang under **AddressSanitizer and UndefinedBehaviorSanitizer**, and runs targeted scenarios against them using hand-written hardware mocks (no STM32 hardware involved).

## What each round validates

| Script | Validates |
|---|---|
| `BUGFIX_ROUND_1_VERIFY.py` | Flash read/write bounds and byte/halfword address-unit handling; UART1/UART3 receive-buffer bounds and termination; truncated/malformed GPS and SMS input parsing safety; MAX30102 startup buffer bounds |
| `BUGFIX_ROUND_2_VERIFY.py` | MAX30102 flat-signal (`un_max == un_min`) divide-by-zero guard; GPS hemisphere sign handling (N/E positive, S/W negative) |
| `BUGFIX_ROUND_3_VERIFY.py` | Cancel button during an active fall suppresses the pending fall SMS and silences the buzzer; cancel after the alarm already fired causes no duplicate SMS; a later, independent fall still alarms normally after recovery (cancel does not permanently disable detection) |
| `BUGFIX_ROUND_4_VERIFY.py` | GSM startup AT-command retry is finite (does not hang firmware boot); `gsm_init()` still returns — with explicit failure — even if every command fails; the normal, successful modem-response path is unchanged |

## Prerequisites

- Python 3
- A Clang toolchain with AddressSanitizer/UndefinedBehaviorSanitizer support (Apple Clang on macOS, or upstream LLVM Clang on Linux). `BUGFIX_ROUND_2_VERIFY.py` additionally uses `-fsanitize=float-divide-by-zero`.
- No other dependencies — each script resolves the firmware path relative to its own location (`../firmware/User/`), so it works from any clone of this repository without edits.

## Running

From the repository root:

```sh
python3 tests/BUGFIX_ROUND_1_VERIFY.py
python3 tests/BUGFIX_ROUND_2_VERIFY.py
python3 tests/BUGFIX_ROUND_3_VERIFY.py
python3 tests/BUGFIX_ROUND_4_VERIFY.py
```

Each prints `PASS` lines for its scenarios and exits 0 on success. Compilation happens in a temporary directory outside the repository; nothing under `firmware/` is modified.

## What this does *not* cover

ASan/UBSan availability depends on your host compiler — these tests will not run without a Clang build that supports them (GCC's sanitizers are not tested here). More importantly: **these are host-side simulations of the extracted C logic, not a Keil/ARMCC build and not a hardware test.** They do not replace rebuilding the firmware with the target toolchain, flashing it to an STM32F103, or re-validating behavior on physical hardware — see [`docs/validation.md`](../docs/validation.md) for the full picture of what has and has not been verified.
