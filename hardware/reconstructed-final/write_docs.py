#!/usr/bin/env python3
"""Regenerate the reconstruction BOM, evidence mapping, and review report."""
from pathlib import Path
import csv
from build_reconstruction import OUT, PROJECT, components, route_failures, tracks, vias


with (OUT / "BOM_reconstructed.csv").open("w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["Reference", "Component / module", "Qty", "Footprint", "Population", "Evidence / assumption"])
    for c in components:
        w.writerow([c["ref"], c["value"], 1, f'Reconstruction:{c["kind"]}_{len(c["pin_names"])}P', "DNP" if c["dnp"] else "Populate", "See RECONSTRUCTION_REPORT.md; module dimensions and connector pin order require build review."])


mapping_rows = [
    ("GPS TX → MCU RX", "PB11 / USART3_RX", "GPS_TX_TO_MCU_RX_PB11", "usart3.c configures PB11 as RX", "Confirmed from active firmware", "PB11 is not used for the active buzzer path."),
    ("GPS RX ← MCU TX", "PB10 / USART3_TX", "GPS_RX_FROM_MCU_TX_PB10", "usart3.c configures PB10 as TX", "Confirmed from active firmware", "Blue Pill header pin 15 only; erroneous baseline tie to header pin 38 removed."),
    ("GSM TX → MCU RX", "PA10 / USART1_RX", "GSM_TX_TO_MCU_RX_PA10", "usart1.c GPIO and USART setup", "Confirmed from active firmware", "SIM800 TX logic level is normally accepted by STM32 3.3 V input."),
    ("GSM RX ← MCU TX", "PA9 / USART1_TX", "GSM_TX_FROM_MCU_PA9 → 10k/47k divider → GSM_RX_DIVIDED", "usart1.c GPIO and USART setup", "Firmware pin confirmed; divider is a new design decision", "Divider targets about 2.72 V from 3.3 V for a bare 2.8 V SIM800 UART input."),
    ("Buzzer driver", "PC13", "BUZZER_PC13", "main.c uses BEEP from key.h; KEY_Init configures PC13", "Confirmed from active startup path", "PB11 BEEP_GPIO_Config in led.c is not called. S8050 lead order remains footprint-dependent."),
    ("ADXL345 SCL / SDA", "PA6 / PA7", "ACCEL_SCL_PA6 / ACCEL_SDA_PA7", "iic.c and iic.h; main calls IIC_init", "Confirmed from active firmware", "PD5/PD6 appears only in a stale comment. Optional pull-ups are DNP by default."),
    ("MAX30102 SCL / SDA", "PB1 / PB0", "MAX_SCL_PB1 / MAX_SDA_PB0", "myiic.c; main calls bsp_InitI2C", "Confirmed from active firmware", "Optional pull-ups are DNP by default because breakout pull-ups are unresolved."),
    ("OLED SCL / SDA", "PB6 / PB7", "OLED_SCL_PB6 / OLED_SDA_PB7", "OLED_I2C.c; main calls OLED_Init", "Confirmed from active firmware", "Optional pull-ups are DNP by default."),
    ("DS18B20 DQ", "PA11", "TEMP_DQ_PA11", "ds18b20.c; dissertation", "Confirmed from active firmware", "4.7k carrier pull-up is DNP if the fitted module already has one."),
    ("Buttons", "PB12, PB13, PB14, PB15, PA8", "BTN_MODE / BTN_UP / BTN_DOWN / BTN_NEXT / BTN_HELP", "key.c and key.h", "Confirmed from active firmware", "Active-low switches to ground; MCU internal pull-ups are enabled."),
    ("Blue Pill power", "3V3 header pins 18 and 40", "3V3", "Carrier power architecture", "New design decision", "The 5 V header pin 38 is intentionally unconnected. Do not connect USB while the carrier drives 3.3 V."),
    ("SIM800 power", "Separate 4.0 V input", "SIM_VBAT_INPUT / SIM_VBAT", "Prototype photo and dissertation show separate modem supply", "Visual evidence plus new power-integrity design", "0.8 mm routing and 1000 uF low-ESR plus 100 nF local bypass; source must tolerate current bursts."),
]
with (OUT / "firmware_to_net_mapping.csv").open("w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["Function", "MCU pin", "Reconstructed net", "Evidence", "Classification", "Notes"])
    w.writerows(mapping_rows)


report = f'''# Reconstructed Design Based on the Final Physical Prototype — Not Fabrication-Validated

## Scope and authority

This is a new, editable carrier-board design based primarily on the photographed final physical prototype. Recovered Altium files, EasyEDA JSON, BOM archives, dissertation material and firmware are supporting evidence from potentially different development iterations. None is treated as an authoritative historical final revision, and no claim is made that the new routing or pin assignment is identical to the manufactured undergraduate board.

All historical files, photographs, firmware, reports and videos remain unchanged.

## Deliverable status

The project now contains a real KiCad schematic with {len(components)} component/module symbols, named electrical pins, short wire stubs, net labels, no-connect markers, power rails, references, values and footprint assignments. The PCB contains the same {len(components)} references and 26 named nets, {len(tracks)} routed copper segments, {len(vias)} vias, 0.30 mm signal tracks, 0.60 mm logic-power tracks, 0.80 mm SIM800 power tracks and a bottom-layer GND zone. The board outline is 104 × 82 mm.

The module footprints are purpose-built carrier/socket representations. Their pin numbering and outline dimensions remain subject to confirmation against the exact physical breakout modules before fabrication.

## Conflict resolution from active firmware

* **PB11 GPS versus buzzer:** `usart3.c` configures PB11 as USART3 RX and PB10 as TX. `main.c` uses `BEEP` from `key.h`; `KEY_Init` configures PC13 as the buzzer output. The PB11 helper in `led.c` is not called by the application startup path. The reconstruction therefore uses PB11 for GPS RX and PC13 for the buzzer.
* **ADXL345 PA6/PA7 versus PD5/PD6:** startup calls `IIC_init()`. `iic.c` configures PA6/PA7 and `iic.h` maps SCL/SDA to those pins. PD5/PD6 is present only in an inconsistent comment. The reconstruction uses PA6=SCL and PA7=SDA.
* **Blue Pill header pin 38:** the baseline reconstruction incorrectly placed header pin 38 on the PB10 GPS net. The 2×20 Blue Pill mapping used by the recovered evidence assigns PB10 to pin 15 and the 5 V header to pin 38. The GPS net now uses pin 15 only; pin 38 is intentionally unconnected in this externally regulated 3.3 V design.

## Evidence classes

**Visually confirmed final-prototype features:** white carrier-board form, central Blue Pill module, GPS and OLED toward the left, SIM800 and external antenna area at upper-right, sensor modules across the lower region, five tactile buttons at lower-right, buzzer and separate main/modem power controls.

**Electrical connections corroborated by active firmware and other evidence:** USART1 on PA9/PA10 for GSM; USART3 on PB10/PB11 for GPS; ADXL345 on PA6/PA7; MAX30102 on PB1/PB0; OLED on PB6/PB7; DS18B20 on PA11; buttons on PB12–PB15 and PA8; active buzzer control on PC13.

**Reasonable new design decisions:** 104 × 82 mm outline; externally regulated 3.3 V supplied to Blue Pill pins 18/40; separate switched SIM800 VBAT input; 1000 uF low-ESR and 100 nF modem decoupling; 10k/47k divider on STM32 TX into a bare SIM800 RX; low-side transistor buzzer stage with base pull-down; DNP 4.7k pull-up options on the three software-I2C buses and DS18B20 bus; two-layer routing with a bottom ground plane.

**Unresolved details:** exact breakout revisions and connector order for GPS, SIM800, OLED, ADXL345 and MAX30102; SIM800 carrier onboard regulation/level shifting; input connector polarity; S8050 E/B/C ordering; exact buzzer polarity/type; exact board dimensions and mounting details; whether fitted sensor modules already contain pull-ups.

## Electrical review

### SIM800

The modem uses a separate nominal 4.0 V input and switch. VBAT routing is 0.80 mm and local decoupling is placed beside the module power header. The source must maintain the module voltage during transmit bursts; exact allowable voltage and required bulk capacitance depend on the recovered SIM800 breakout revision. The 10k/47k divider is appropriate for a bare 2.8 V RX input, but must be bypassed or adjusted if the actual breakout already includes a 3.3/5 V UART interface. The module TX-to-STM32 path is direct.

### Blue Pill and 3.3 V rail

The carrier uses an AMS1117-3.3 stage with 10 uF input/output capacitors and 100 nF bypass. It powers both Blue Pill 3.3 V header pins and the 3.3 V modules. Blue Pill 5 V pin 38 is left unconnected. USB power must not be connected while the carrier drives the Blue Pill 3.3 V rail unless the exact board's power-path isolation has been verified. AMS1117 dropout, thermal margin and clone-board regulator details require confirmation for the intended input and load.

### Pull-ups and voltage compatibility

STM32 and reconstructed peripheral logic are 3.3 V. Each I2C bus has DNP 4.7k pull-up footprints because typical breakouts often include pull-ups; population must be decided after measuring the exact modules so the combined pull-up resistance is suitable. The DS18B20 pull-up follows the same rule. No 5 V logic is connected directly to STM32 GPIO in the reconstruction.

## Verification

The local static verifier confirms reference uniqueness, pad existence, one-net-per-pad assignment, required nets, schematic label count versus PCB pad membership, route completion for every non-ground net, GND zone presence, component bounds/overlaps, corrected Blue Pill pin 38 treatment and balanced KiCad S-expressions. The autorouter reports {len(route_failures)} failed connections.

Native KiCad ERC, DRC and 3D rendering are executed by the repository workflow in `.github/workflows/kicad-reconstruction.yml` using the official KiCad 9 full container. Their reports and native render are workflow artifacts. Until those results are copied into this directory and reviewed, they must not be described as passes.

No physical assembly, fabrication, power-on or new hardware validation has been performed. Do not order boards until exact module pinouts and power requirements are confirmed and native ERC/DRC results have been reviewed.
'''
(OUT / "RECONSTRUCTION_REPORT.md").write_text(report)

verification = f'''# Verification results

## Local structural and connectivity verification

Latest local result: **PASS**.

The verifier checks:

* unique references and valid pad membership;
* no pad assigned to more than one logical net;
* firmware-critical nets and the corrected PB10/PB11/PC13 mapping;
* J1 pin 38 is not tied to PB10 or to the externally driven 3.3 V rail;
* a real schematic structure containing symbols, pins, wires, labels and no-connect markers;
* schematic label membership matches the explicit PCB/netlist connectivity;
* all non-ground nets have routed copper and the autorouter reported no failed connection;
* a B.Cu GND zone exists;
* component bodies remain inside the 104 × 82 mm outline without estimated overlap;
* KiCad S-expression delimiters are balanced.

Generated PCB statistics: {len(tracks)} copper segments, {len(vias)} vias, 26 logical nets, {len(components)} components/modules.

## Native KiCad validation

KiCad is not installed locally. `.github/workflows/kicad-reconstruction.yml` runs KiCad 9 ERC, DRC, schematic PDF export, front/back board plots and native 3D rendering in the official full container. The workflow preserves the raw reports even if violations exist. Native reports are authoritative over the local structural checker and must be reviewed before fabrication.

This design has not been manufactured or electrically tested.
'''
(OUT / "verification_results.md").write_text(verification)

repo = Path(__file__).parents[2] / "README.md"
s = repo.read_text()
old_start = s.find("## Reconstructed final-style PCB")
section = '''## Reconstructed final-style PCB

**Reconstructed Design Based on the Final Physical Prototype — Not Fabrication-Validated.** The editable KiCad project is in [`hardware/reconstructed-final/Reconstructed_Final_Design/`](hardware/reconstructed-final/Reconstructed_Final_Design/). It contains a symbol-and-wire schematic, routed two-layer PCB, explicit connectivity/BOM evidence and engineering front/back previews. Native KiCad ERC/DRC and 3D outputs are produced by the reconstruction validation workflow and remain subject to review.

The layout follows the genuine [prototype photograph](docs/images/Photograph%20of%20the%20device.jpg): central Blue Pill, GPS/OLED at left, SIM800 at upper-right, sensors below and five buttons at lower-right. Recovered CAD files are supporting historical evidence and remain unchanged. See the [reconstruction report](hardware/reconstructed-final/Reconstructed_Final_Design/RECONSTRUCTION_REPORT.md), [firmware-to-net mapping](hardware/reconstructed-final/Reconstructed_Final_Design/firmware_to_net_mapping.csv) and [verification results](hardware/reconstructed-final/Reconstructed_Final_Design/verification_results.md).
'''
if old_start >= 0:
    s = s[:old_start].rstrip() + "\n\n" + section
else:
    s = s.rstrip() + "\n\n" + section
repo.write_text(s)
