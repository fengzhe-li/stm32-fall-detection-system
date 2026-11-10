# Reconstructed Design Based on the Final Physical Prototype — Not Fabrication-Validated

## Summary

This new carrier-board reconstruction follows the photographed final assembly. It does not claim to reproduce a recovered Altium revision or exact historical copper. It represents the STM32F103C8T6 controller, GPS/OLED, SIM800, ADXL345, MAX30102, DS18B20, power, buzzer and five user buttons as explicit nets. All recovered Altium, EasyEDA, BOM, dissertation, firmware, photos and video remain unchanged.

The photo shows a white carrier board; a Blue Pill style controller near centre; GPS/OLED at left; SIM800 with external antenna at upper-right; sensor breakouts at lower-left and lower-centre; five tactile buttons at lower-right; and separate main/modem power controls. The new 104 × 82 mm outline is an approximate layout choice, not a calibrated measurement.

## Conflicts resolved from active code

* **PB11 GPS versus buzzer:** `usart3.c` configures PB11 as USART3 RX and PB10 as TX. `main.c` includes `key.h`, not `led.h`; `key.h` maps `BEEP` to PC13, which `KEY_Init` configures as an output. `led.c` has a separate PB11 buzzer initializer, but `BEEP_GPIO_Config()` is not called from the application startup path. The reconstruction therefore uses PB11 for GPS RX and PC13 for the buzzer without changing firmware.
* **ADXL345 PA6/PA7 versus PD5/PD6:** startup calls `IIC_init()`. `iic.c` enables GPIOA and configures pins 6/7; `iic.h` maps SCL/SDA to PA6/PA7; dissertation text independently states PA6/PA7. PD5/PD6 appears only in an inconsistent driver comment. The reconstruction uses PA6=SCL and PA7=SDA.

## Evidence classes

**Visually confirmed:** carrier-board grouping, controller module, GPS/OLED left, SIM800/antenna top-right, sensor breakouts, five buttons, separate power controls. Exact connector pin order, board dimensions and copper are not visible.

**Cross-source electrical evidence:** GSM USART1 PA9/PA10; GPS USART3 PB10/PB11; ADXL345 I2C PA6/PA7; MAX30102 I2C PB1/PB0; OLED I2C PB6/PB7; DS18B20 PA11; buttons PB12–PB15/PA8; buzzer PC13 in the active source path. Details are in `firmware_to_net_mapping.csv`.

**New design choices:** 104 × 82 mm outline; 2.54 mm connectors; separate 5 V logic input and nominal 4 V SIM800 input/switch; AMS1117-3.3 regulator with 10 μF input/output and 100 nF bypass capacitors; 10 kΩ DS18B20 pull-up; S8050 low-side buzzer stage with 1 kΩ base resistor. Blue Pill header pad mapping follows the recovered 20-pin header assignment; clone-board variants and S8050 lead assignment remain unverified.

## Electrical limitations

SIM800 needs a low-impedance supply with burst-current capacity. The design represents a separate modem supply; exact voltage, current rating, capacitance/ESR, polarity and module pinout remain unresolved. Confirm the exact modem breakout before powering it. The 3.3 V rail is represented by an AMS1117-3.3 and bypass capacitors, but its thermal margin and module load have not been checked. Sensor/OLED module pull-ups and voltage translation are also unknown. Do not apply USB power to a Blue Pill simultaneously with externally driving its 3.3 V header. No RF antenna design is added because the prototype uses a commercial module and antenna.

## CAD and verification status

The package has editable KiCad-format PCB and pin/net schedule sources, explicit `.net` and JSON connectivity, BOM and mapping CSVs, and SVG/PNG previews. The `.kicad_sch` is an editable textual pin/net schedule rather than a symbol-and-wire schematic. The PCB contains component placements and pad/net assignments, but **has no copper tracks or verified zones**. KiCad is not installed in this environment, so native ERC/DRC and KiCad 3D export could not be run. `verify_design.py` checks reference uniqueness, pad membership, required nets, estimated body bounds/overlaps and S-expression balance only; it is not an ERC/DRC substitute. The isometric render is an illustrative assembly preview, not a native 3D board render. This package is not suitable for fabrication.

## Remaining uncertainties

1. Exact Blue Pill pin order and board regulator/USB details.
2. GPS, SIM800, OLED, MAX30102 and ADXL345 breakout pin order and onboard regulators/level shifters.
3. SIM800 power variant, burst current and required local decoupling.
4. S8050 manufacturer/lead order and buzzer type/polarity.
5. Whether DS18B20 module already includes a pull-up; exact input jack polarity and board dimensions.
6. Recovered Altium/BOM files may represent other iterations; none is treated as authoritative final.

No firmware was changed. No physical assembly, manufacturing, power-on or new hardware validation is claimed.
