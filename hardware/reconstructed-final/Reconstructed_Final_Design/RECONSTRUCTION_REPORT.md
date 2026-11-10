# Reconstructed Design Based on the Final Physical Prototype — Not Fabrication-Validated

## Scope and authority

This is a new, editable carrier-board design based primarily on the photographed final physical prototype. Recovered Altium files, EasyEDA JSON, BOM archives, dissertation material and firmware are supporting evidence from potentially different development iterations. None is treated as an authoritative historical final revision, and no claim is made that the new routing or pin assignment is identical to the manufactured undergraduate board.

All historical files, photographs, firmware, reports and videos remain unchanged.

## Deliverable status

The project now contains a real KiCad schematic with 36 component/module symbols, named electrical pins, short wire stubs, net labels, no-connect markers, power rails, references, values and footprint assignments. The PCB contains the same 36 references and 26 named nets, 274 routed copper segments, 14 vias, 0.30 mm signal tracks, 0.60 mm logic-power tracks, 0.80 mm SIM800 power tracks and a bottom-layer GND zone. The board outline is 104 × 82 mm.

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

The local static verifier confirms reference uniqueness, pad existence, one-net-per-pad assignment, required nets, schematic label count versus PCB pad membership, route completion for every non-ground net, GND zone presence, component bounds/overlaps, corrected Blue Pill pin 38 treatment and balanced KiCad S-expressions. The autorouter reports 0 failed connections.

Native KiCad ERC, DRC and 3D rendering are executed by the repository workflow in `.github/workflows/kicad-reconstruction.yml` using the official KiCad 9 full container. Their reports and native render are workflow artifacts. Until those results are copied into this directory and reviewed, they must not be described as passes.

No physical assembly, fabrication, power-on or new hardware validation has been performed. Do not order boards until exact module pinouts and power requirements are confirmed and native ERC/DRC results have been reviewed.
