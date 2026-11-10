# Verification results

**Status: static connectivity checks passed; native ERC/DRC not run.**

`python3 hardware/reconstructed-final/verify_design.py` checks:

- unique component references;
- that every netlist pad exists on a listed footprint;
- that no pad is assigned to multiple nets;
- that required controller/peripheral nets are present;
- balanced S-expression delimiters in the generated `.kicad_pcb` and `.kicad_sch`;
- estimated component-body bounds and overlap against the 104 × 82 mm outline.

Latest result: **PASS**, with no estimated component-body overlaps or out-of-outline bodies. The script also reports that the PCB has no copper segments. This means connected pads share a named logical net in the CAD data, but copper connectivity is not physically routed.

KiCad (`kicad-cli`, `pcbnew`, `eeschema`) is not installed in this environment. Therefore KiCad parser validation, ERC, DRC, connectivity-from-copper, footprint library resolution, solder-mask clearance, unconnected-item reports, and native 3D rendering could not be performed. These are not reported as passes. Do not use this board to order fabrication.
