# Verification results

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
* inter-net track, pad and via geometry meets the local 0.25 mm clearance calculation;
* component bodies remain inside the 104 × 82 mm outline without estimated overlap;
* KiCad S-expression delimiters are balanced.

Generated PCB statistics: 274 copper segments, 14 vias, 26 logical nets, 36 components/modules.

## Native KiCad validation

KiCad is not installed locally. `.github/workflows/kicad-reconstruction.yml` is configured to run KiCad 9 ERC, DRC, schematic PDF export and native front/back 3D rendering in the official full container. It preserves raw reports even if violations exist. No native output is present at this commit, so native ERC/DRC and 3D export remain unverified. Native reports are authoritative over the local structural checker and must be reviewed before fabrication.

This design has not been manufactured or electrically tested.
