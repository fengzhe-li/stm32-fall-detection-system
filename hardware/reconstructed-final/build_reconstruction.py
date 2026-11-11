#!/usr/bin/env python3
"""Generate the editable KiCad reconstruction, routed PCB, and previews."""
from pathlib import Path
from collections import defaultdict
import heapq
import json
import math
import re
import subprocess
import uuid

ROOT = Path(__file__).parent
OUT = ROOT / "Reconstructed_Final_Design"
OUT.mkdir(exist_ok=True)
PROJECT = "FallDetection_Reconstructed"
LABEL = "Reconstructed Design Based on the Final Physical Prototype — Not Fabrication-Validated"
NS = uuid.UUID("72f54bc9-9df4-4a52-929d-cf9258bb34ac")
uid = lambda name: str(uuid.uuid5(NS, name))

W, H = 104.0, 82.0
SIZES = {
    "controller": (25.4, 53.3), "power": (10.0, 8.0),
    "sensor": (18.0, 14.0), "temp_sensor": (12.0, 8.0), "module": (22.0, 16.0),
    "button": (7.0, 7.0), "switch": (9.0, 6.0),
    "resistor": (9.0, 4.0), "resistor_smd": (2.4, 1.4),
    "transistor": (6.0, 5.0), "buzzer": (12.0, 12.0),
    "regulator": (11.0, 8.0), "capacitor": (5.0, 5.0),
    "capacitor_large": (11.0, 11.0),
}


def comp(ref, value, x, y, kind, pin_names, pin_types=None, dnp=False):
    if pin_types is None:
        pin_types = ["passive"] * len(pin_names)
    return {"ref": ref, "value": value, "x": x, "y": y, "kind": kind,
            "pin_names": pin_names, "pin_types": pin_types, "dnp": dnp}


bluepill_pins = [
    "VBAT", "PC13", "PC14", "PC15", "PA0", "PA1", "PA2", "PA3",
    "PA4", "PA5", "PA6", "PA7", "PB0", "PB1", "PB10", "PB11",
    "NRST", "3V3_A", "GND_A", "GND_B", "PB12", "PB13", "PB14",
    "PB15", "PA8", "PA9", "PA10", "PA11", "PA12", "PA15", "PB3",
    "PB4", "PB5", "PB6", "PB7", "PB8", "PB9", "5V", "GND_C", "3V3_B",
]

components = [
    comp("J1", "STM32F103C8T6 Blue Pill socket", 55, 38, "controller", bluepill_pins,
         ["power_in"] + ["bidirectional"] * 15 + ["input", "power_in", "power_in", "power_in"] + ["bidirectional"] * 17 + ["power_in", "power_in", "power_in"]),
    comp("J2", "Main 5 V input", 7, 7, "power", ["5V_IN", "GND"], ["power_out", "power_out"]),
    comp("J3", "SIM800 4.0 V input", 97, 7, "power", ["VBAT_IN", "GND"], ["power_out", "power_out"]),
    comp("J4", "DS18B20 module", 15, 31, "temp_sensor", ["VCC", "GND", "DQ"], ["power_in", "power_in", "bidirectional"]),
    comp("J5", "VK2828U7G5LF GPS module", 24, 18, "module", ["VCC", "GND", "TX", "RX"], ["power_in", "power_in", "output", "input"]),
    comp("J6", "ADXL345 breakout", 26, 72, "sensor", ["VCC", "GND", "SCL", "SDA"], ["power_in", "power_in", "bidirectional", "bidirectional"]),
    comp("J7", "MAX30102 breakout", 49, 72, "sensor", ["VCC", "GND", "SCL", "SDA"], ["power_in", "power_in", "bidirectional", "bidirectional"]),
    comp("J8", "0.96 inch OLED I2C module", 16, 48, "module", ["VCC", "GND", "SCL", "SDA"], ["power_in", "power_in", "bidirectional", "bidirectional"]),
    comp("J9", "SIM800 power header", 99, 41, "power", ["VBAT", "GND"], ["power_in", "power_in"]),
    comp("J10", "SIM800 UART / PWRKEY header", 88, 21, "module", ["PWRKEY_NC", "GND", "TXD", "RXD"], ["input", "power_in", "output", "input"]),
    comp("SW1", "Mode button", 72, 59, "button", ["SIG", "GND"]),
    comp("SW2", "Up button", 81, 59, "button", ["SIG", "GND"]),
    comp("SW3", "Down button", 71, 70, "button", ["SIG", "GND"]),
    comp("SW4", "Next button", 81, 70, "button", ["SIG", "GND"]),
    comp("SW5", "Help button", 92, 70, "button", ["SIG", "GND"]),
    comp("SW6", "GSM VBAT switch", 99, 49, "switch", ["OUT", "IN"], ["power_out", "passive"]),
    comp("SW7", "Main power switch", 8, 17, "switch", ["OUT", "IN"], ["power_out", "passive"]),
    comp("R1", "4.7k DS18B20 pull-up (DNP if module fitted)", 29, 31, "resistor", ["DQ", "3V3"], dnp=True),
    comp("R2", "1k buzzer base resistor", 78, 49, "resistor", ["PC13", "BASE"]),
    comp("R3", "10k SIM800 RX divider upper", 72, 18, "resistor", ["PA9", "RX_DIV"]),
    comp("R4", "47k SIM800 RX divider lower", 72, 25, "resistor", ["RX_DIV", "GND"]),
    comp("R5", "4.7k ADXL SCL pull-up (DNP)", 15.5, 67, "resistor_smd", ["SCL", "3V3"], dnp=True),
    comp("R6", "4.7k ADXL SDA pull-up (DNP)", 15.5, 72, "resistor_smd", ["SDA", "3V3"], dnp=True),
    comp("R7", "4.7k MAX SCL pull-up (DNP)", 37.5, 67, "resistor_smd", ["SCL", "3V3"], dnp=True),
    comp("R8", "4.7k MAX SDA pull-up (DNP)", 37.5, 72, "resistor_smd", ["SDA", "3V3"], dnp=True),
    comp("R9", "4.7k OLED SCL pull-up (DNP)", 29.5, 43, "resistor_smd", ["SCL", "3V3"], dnp=True),
    comp("R10", "4.7k OLED SDA pull-up (DNP)", 29.5, 54, "resistor_smd", ["SDA", "3V3"], dnp=True),
    comp("R11", "10k buzzer base pull-down", 74, 36, "resistor", ["BASE", "GND"]),
    comp("Q1", "S8050 low-side buzzer driver", 87, 51, "transistor", ["E", "C", "B"], ["passive", "passive", "input"]),
    comp("BZ1", "5 V active buzzer", 96, 59, "buzzer", ["+", "-"]),
    comp("U1", "AMS1117-3.3 regulator module", 44, 7, "regulator", ["GND", "OUT", "IN"], ["power_in", "power_out", "power_in"]),
    comp("C1", "10 uF regulator input", 34, 7, "capacitor", ["+", "-"]),
    comp("C2", "10 uF regulator output", 53, 7, "capacitor", ["+", "-"]),
    comp("C3", "100 nF regulator bypass", 61, 7, "capacitor", ["1", "2"]),
    comp("C4", "1000 uF low-ESR SIM800 bulk", 88, 39, "capacitor_large", ["+", "-"]),
    comp("C5", "100 nF SIM800 bypass", 80, 42, "capacitor", ["1", "2"]),
]
# PC13 actively drives the buzzer transistor network in the released firmware.
# Model it as an output so ERC can verify that Q1's base is driven through R2.
components[0]["pin_types"][1] = "output"
by_ref = {c["ref"]: c for c in components}

nets = {
    "GND": ["J1.19", "J1.20", "J1.39", "J2.2", "J3.2", "J4.2", "J5.2", "J6.2", "J7.2", "J8.2", "J9.2", "J10.2", "SW1.2", "SW2.2", "SW3.2", "SW4.2", "SW5.2", "Q1.1", "U1.1", "C1.2", "C2.2", "C3.2", "C4.2", "C5.2", "R4.2", "R11.2"],
    "+5V_INPUT": ["J2.1", "SW7.2"], "+5V": ["SW7.1", "U1.3", "C1.1", "BZ1.1"],
    "SIM_VBAT_INPUT": ["J3.1", "SW6.2"], "SIM_VBAT": ["SW6.1", "J9.1", "C4.1", "C5.1"],
    "3V3": ["J1.18", "J1.40", "J4.1", "J5.1", "J6.1", "J7.1", "J8.1", "R1.2", "U1.2", "C2.1", "C3.1", "R5.2", "R6.2", "R7.2", "R8.2", "R9.2", "R10.2"],
    "GPS_TX_TO_MCU_RX_PB11": ["J1.16", "J5.3"], "GPS_RX_FROM_MCU_TX_PB10": ["J1.15", "J5.4"],
    "GSM_TX_TO_MCU_RX_PA10": ["J1.27", "J10.3"], "GSM_TX_FROM_MCU_PA9": ["J1.26", "R3.1"],
    "GSM_RX_DIVIDED": ["R3.2", "R4.1", "J10.4"],
    "ACCEL_SCL_PA6": ["J1.11", "J6.3", "R5.1"], "ACCEL_SDA_PA7": ["J1.12", "J6.4", "R6.1"],
    "MAX_SCL_PB1": ["J1.14", "J7.3", "R7.1"], "MAX_SDA_PB0": ["J1.13", "J7.4", "R8.1"],
    "OLED_SCL_PB6": ["J1.34", "J8.3", "R9.1"], "OLED_SDA_PB7": ["J1.35", "J8.4", "R10.1"],
    "TEMP_DQ_PA11": ["J1.28", "J4.3", "R1.1"], "BUZZER_PC13": ["J1.2", "R2.1"],
    "BUZZER_BASE": ["R2.2", "R11.1", "Q1.3"], "BUZZER_LOW_SIDE": ["Q1.2", "BZ1.2"],
    "BTN_MODE_PB12": ["J1.21", "SW1.1"], "BTN_UP_PB13": ["J1.22", "SW2.1"],
    "BTN_DOWN_PB14": ["J1.23", "SW3.1"], "BTN_NEXT_PB15": ["J1.24", "SW4.1"], "BTN_HELP_PA8": ["J1.25", "SW5.1"],
}
padnet = {pad: net for net, pads in nets.items() for pad in pads}
net_index = {net: i for i, net in enumerate(nets, 1)}


def pad_position(c, pin):
    kind, count = c["kind"], len(c["pin_names"])
    if kind == "controller":
        return (-7.62 if pin <= 20 else 7.62, ((pin - 1) % 20) * 2.54 - 24.13)
    if kind in {"module", "sensor", "temp_sensor"}:
        return ((pin - (count + 1) / 2) * 2.54, SIZES[kind][1] / 2 - 2.0)
    if kind in {"resistor", "switch"}:
        spacing = 7.62 if kind == "resistor" else 5.08
        return (-spacing / 2 if pin == 1 else spacing / 2, 0)
    if kind == "resistor_smd": return (-0.8 if pin == 1 else 0.8, 0)
    if kind == "button": return (-3.25 if pin == 1 else 3.25, 0)
    if kind in {"transistor", "regulator"}: return ((pin - 2) * 2.54, 0)
    if kind in {"capacitor", "capacitor_large"}:
        spacing = 2.5 if kind == "capacitor" else 5.0
        return (-spacing / 2 if pin == 1 else spacing / 2, 0)
    if kind == "buzzer": return (-3.75 if pin == 1 else 3.75, 0)
    if count == 2: return (-2.54 if pin == 1 else 2.54, 0)
    return ((pin - (count + 1) / 2) * 2.54, 0)


def abs_pad(ref, pin):
    c = by_ref[ref]; dx, dy = pad_position(c, pin)
    return c["x"] + dx, c["y"] + dy


def pcb_footprint(c):
    ref, value, kind = c["ref"], c["value"], c["kind"]
    fw, fh = SIZES[kind]; smd = kind == "resistor_smd"
    lines = [f'  (footprint "Reconstruction:{kind}_{len(c["pin_names"])}P" (layer "F.Cu") (uuid "{uid("fp-"+ref)}") (at {c["x"]} {c["y"]})',
             f'    (property "Reference" "{ref}" (at 0 {-fh/2-1.5:.2f} 0) (layer "F.SilkS") (uuid "{uid("fp-ref-"+ref)}") (effects (font (size 1 1) (thickness 0.15))))',
             f'    (property "Value" "{value}" (at 0 {fh/2+1.5:.2f} 0) (layer "F.Fab") (uuid "{uid("fp-value-"+ref)}") (effects (font (size 0.8 0.8) (thickness 0.12))))',
             f'    (attr {"smd" if smd else "through_hole"})',
             f'    (fp_rect (start {-fw/2:.2f} {-fh/2:.2f}) (end {fw/2:.2f} {fh/2:.2f}) (stroke (width 0.15) (type default)) (fill none) (layer "F.SilkS") (uuid "{uid("fp-silk-"+ref)}"))',
             f'    (fp_rect (start {-fw/2:.2f} {-fh/2:.2f}) (end {fw/2:.2f} {fh/2:.2f}) (stroke (width 0.05) (type default)) (fill none) (layer "F.Fab") (uuid "{uid("fp-fab-"+ref)}"))',
             f'    (fp_rect (start {-fw/2-0.25:.2f} {-fh/2-0.25:.2f}) (end {fw/2+0.25:.2f} {fh/2+0.25:.2f}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd") (uuid "{uid("fp-courtyard-"+ref)}"))']
    for pin, name in enumerate(c["pin_names"], 1):
        px, py = pad_position(c, pin); net = padnet.get(f"{ref}.{pin}")
        net_clause = f' (net {net_index[net]} "{net}")' if net else ""
        if smd:
            lines.append(f'    (pad "{pin}" smd roundrect (at {px:.3f} {py:.3f}) (size 1.1 1.2) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2){net_clause} (uuid "{uid(f"pad-{ref}-{pin}")}"))')
        else:
            shape = "rect" if pin == 1 else "circle"; drill = 1.0 if kind in {"power","switch","buzzer","capacitor_large"} else 0.9; size = 2.1 if drill == 1.0 else 1.8
            lines.append(f'    (pad "{pin}" thru_hole {shape} (at {px:.3f} {py:.3f}) (size {size} {size}) (drill {drill}) (layers "*.Cu" "*.Mask"){net_clause} (uuid "{uid(f"pad-{ref}-{pin}")}"))')
        lines.append(f'    (fp_text user "{name}" (at {px:.3f} {py-1.6:.3f}) (layer "F.Fab") (uuid "{uid(f"fp-pin-text-{ref}-{pin}")}") (effects (font (size 0.55 0.55) (thickness 0.08))))')
    lines += ['    (embedded_fonts no)', '  )']
    return '\n'.join(lines)


def autoroute():
    # A 0.5 mm grid plus one-cell track envelopes provides at least 0.25 mm
    # copper clearance for 0.30 mm signal tracks.
    step = 0.5; nx, ny = int(W/step)+1, int(H/step)+1
    pad_cells = []
    for c in components:
        for pin in range(1, len(c["pin_names"])+1):
            token = f'{c["ref"]}.{pin}'
            net = padnet.get(token)
            x, y = abs_pad(c["ref"], pin); layers = {0} if c["kind"] == "resistor_smd" else {0,1}
            # Unassigned pads are still copper obstacles.  Previously they
            # were omitted here, allowing routed signals to cross Blue Pill
            # and header pads that intentionally have no net.
            obstacle_owner = net if net else f'__UNASSIGNED__{token}'
            pad_cells.append((round(x/step), round(y/step), obstacle_owner, layers, 2 if c["kind"] == "resistor_smd" else 3))
    occupied = [defaultdict(set), defaultdict(set)]; tracks, vias, failures = [], [], []
    def blocked_by_pad(x, y, layer, net):
        return any(pnet != net and layer in layers and (px-x)**2+(py-y)**2 <= radius**2 for px,py,pnet,layers,radius in pad_cells)
    def via_blocked_by_pad(x, y, net):
        # A 1.0 mm via needs one additional 0.5 mm grid cell of separation
        # beyond the signal-track envelope on both copper layers.
        return any(pnet != net and (px-x)**2+(py-y)**2 <= (radius+1)**2 for px,py,pnet,layers,radius in pad_cells)
    def route_pair(net, start, goal, start_layers, goal_layers, width):
        sx,sy = round(start[0]/step),round(start[1]/step); gx,gy = round(goal[0]/step),round(goal[1]/step)
        q=[]; best={}; prev={}; starts=[]
        for layer in start_layers:
            state=(sx,sy,layer,4); starts.append(state); best[state]=0; heapq.heappush(q,(abs(sx-gx)+abs(sy-gy),0,state))
        end=None
        while q:
            _,cost,state=heapq.heappop(q)
            if cost != best.get(state): continue
            x,y,layer,direction=state
            if x==gx and y==gy and layer in goal_layers: end=state; break
            for nd,(dx,dy) in enumerate(((1,0),(-1,0),(0,1),(0,-1))):
                xx,yy=x+dx,y+dy
                if not (3<=xx<nx-3 and 3<=yy<ny-3) or blocked_by_pad(xx,yy,layer,net): continue
                bad=False
                for ox in (-1,0,1):
                    for oy in (-1,0,1):
                        owners=occupied[layer].get((xx+ox,yy+oy),set())
                        if owners and owners != {net}: bad=True
                if bad: continue
                nc=cost+1+(0.35 if direction not in (4,nd) else 0); ns=(xx,yy,layer,nd)
                if nc < best.get(ns,1e30): best[ns]=nc; prev[ns]=state; heapq.heappush(q,(nc+abs(xx-gx)+abs(yy-gy),nc,ns))
            other=1-layer
            if not blocked_by_pad(x,y,other,net) and not via_blocked_by_pad(x,y,net):
                o0=occupied[layer].get((x,y),set()); o1=occupied[other].get((x,y),set())
                if (not o0 or o0=={net}) and (not o1 or o1=={net}):
                    ns=(x,y,other,4); nc=cost+9
                    if nc < best.get(ns,1e30): best[ns]=nc; prev[ns]=state; heapq.heappush(q,(nc+abs(x-gx)+abs(y-gy),nc,ns))
        if end is None: return None
        path=[end]
        while path[-1] not in starts: path.append(prev[path[-1]])
        return list(reversed(path))
    power_nets=["+5V_INPUT","+5V","SIM_VBAT_INPUT","SIM_VBAT","3V3"]
    dense_interfaces=["MAX_SDA_PB0","MAX_SCL_PB1","OLED_SDA_PB7","OLED_SCL_PB6","ACCEL_SDA_PA7","ACCEL_SCL_PA6"]
    ordered=dense_interfaces+[n for n in nets if n not in power_nets+dense_interfaces and n!="GND"]+power_nets
    for net in ordered:
        terminals=[]
        for token in nets[net]:
            ref,pin_s=token.split('.'); c=by_ref[ref]; terminals.append((token,abs_pad(ref,int(pin_s)),{0} if c["kind"]=="resistor_smd" else {0,1}))
        if len(terminals)<2: continue
        width=0.8 if net.startswith("SIM_VBAT") else (0.6 if net in {"+5V_INPUT","+5V","3V3"} else 0.3)
        connected=[terminals.pop(0)]
        # The explicit net order lists the MCU and module first, followed by
        # optional pull-up branches. Preserve that primary route before adding
        # DNP branches so an unpopulated option cannot obstruct the interface.
        primary_pending = bool(terminals) and net not in power_nets and len(terminals) > 1
        while terminals:
            if primary_pending:
                a, b = connected[0], terminals[0]
                primary_pending = False
            else:
                _,a,b=min(((math.dist(a[1],b[1]),a,b) for a in connected for b in terminals),key=lambda z:z[0])
            path=route_pair(net,a[1],b[1],a[2],b[2],width)
            if path is None:
                failures.append(f"{net}: {a[0]} to {b[0]}"); terminals.remove(b); connected.append(b); continue
            first=path[0]; last=path[-1]
            if (first[0]*step,first[1]*step)!=a[1]: tracks.append((net,a[1],(first[0]*step,first[1]*step),first[2],width))
            run_start=path[0]; previous=path[0]; run_direction=None
            for current in path[1:]:
                if current[2] != previous[2]:
                    if run_start[:2] != previous[:2]:
                        tracks.append((net,(run_start[0]*step,run_start[1]*step),(previous[0]*step,previous[1]*step),previous[2],width))
                    vias.append((net,(previous[0]*step,previous[1]*step)))
                    run_start=current; run_direction=None
                else:
                    direction=(current[0]-previous[0],current[1]-previous[1])
                    if run_direction is None:
                        run_direction=direction
                    elif direction != run_direction:
                        tracks.append((net,(run_start[0]*step,run_start[1]*step),(previous[0]*step,previous[1]*step),previous[2],width))
                        run_start=previous; run_direction=direction
                previous=current
            if run_start[:2] != previous[:2]:
                tracks.append((net,(run_start[0]*step,run_start[1]*step),(previous[0]*step,previous[1]*step),previous[2],width))
            if (last[0]*step,last[1]*step)!=b[1]: tracks.append((net,(last[0]*step,last[1]*step),b[1],last[2],width))
            radius=2 if width>=0.6 else 1
            for x,y,layer,_ in path:
                for ox in range(-radius,radius+1):
                    for oy in range(-radius,radius+1):
                        if ox*ox+oy*oy<=radius*radius: occupied[layer][(x+ox,y+oy)].add(net)
            for via_net, (via_x, via_y) in vias:
                if via_net != net:
                    continue
                vx, vy = round(via_x/step), round(via_y/step)
                for layer in (0, 1):
                    for ox in range(-2, 3):
                        for oy in range(-2, 3):
                            if ox*ox+oy*oy <= 4:
                                occupied[layer][(vx+ox,vy+oy)].add(net)
            connected.append(b); terminals.remove(b)
    return tracks,vias,failures


tracks,vias,route_failures=autoroute()
board=['(kicad_pcb (version 20241229) (generator "reconstruction_generator") (generator_version "2.0")','  (general (thickness 1.6))','  (paper "A4")','  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user "b.adhesive") (33 "F.Adhes" user "f.adhesive") (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user "b.courtyard") (47 "F.CrtYd" user "f.courtyard") (48 "B.Fab" user) (49 "F.Fab" user))','  (setup (pad_to_mask_clearance 0))']
for net,idx in net_index.items(): board.append(f'  (net {idx} "{net}")')
for c in components: board.append(pcb_footprint(c))
for i,(net,a,b,layer,width) in enumerate(tracks):
    if math.dist(a,b)>0.01: board.append(f'  (segment (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (width {width:.2f}) (layer "{"F.Cu" if layer==0 else "B.Cu"}") (net {net_index[net]}) (uuid "{uid(f"seg-{i}-{net}-{a}-{b}")}"))')
for i,(net,p) in enumerate(vias): board.append(f'  (via (at {p[0]:.3f} {p[1]:.3f}) (size 1.0) (drill 0.5) (layers "F.Cu" "B.Cu") (net {net_index[net]}) (uuid "{uid(f"via-{i}-{net}-{p}")}"))')
board += [f'  (zone (net {net_index["GND"]}) (net_name "GND") (layer "B.Cu") (uuid "{uid("gnd-zone")}") (hatch edge 0.5) (connect_pads (clearance 0.3)) (min_thickness 0.25) (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4)) (polygon (pts (xy 1 1) (xy {W-1} 1) (xy {W-1} {H-1}) (xy 1 {H-1}))))',f'  (gr_rect (start 0 0) (end {W} {H}) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts") (uuid "{uid("outline")}"))',f'  (gr_text "RECONSTRUCTED FINAL DESIGN / NOT FABRICATION-VALIDATED" (at 52 3) (layer "F.SilkS") (uuid "{uid("title-front")}") (effects (font (size 1.3 1.3) (thickness 0.2))))',f'  (gr_text "STM32 FALL DETECTION + HEALTH MONITOR" (at 52 79) (layer "F.SilkS") (uuid "{uid("title-bottom")}") (effects (font (size 1.2 1.2) (thickness 0.2))))',f'  (gr_text "GND PLANE / MODULE PINOUTS REQUIRE BUILD REVIEW" (at 52 79) (layer "B.SilkS") (uuid "{uid("title-back")}") (effects (font (size 1.0 1.0) (thickness 0.16)) (justify mirror)))',')']
(OUT/f'{PROJECT}.kicad_pcb').write_text('\n'.join(board)+'\n')
(OUT/f'{PROJECT}.kicad_pro').write_text(json.dumps({"board":{},"boards":[],"cvpcb":{},"erc":{},"libraries":{},"meta":{"filename":f"{PROJECT}.kicad_pro","version":1},"net_settings":{},"pcbnew":{},"schematic":{},"text_variables":{}},indent=2)+'\n')
(OUT/f'{PROJECT}.kicad_dru').write_text('(version 1)\n(rule "Copper clearance" (constraint clearance (min 0.25mm)))\n(rule "Signal track width" (constraint track_width (min 0.30mm)))\n(rule "Via size" (constraint via_diameter (min 1.0mm)) (constraint hole_size (min 0.5mm)))\n(rule "Board edge clearance" (constraint edge_clearance (min 0.25mm)))\n')


def effects(hidden=False,justify=None):
    extra=f' (justify {justify})' if justify else ''
    return f'(effects (font (size 1.27 1.27)){extra}{" (hide yes)" if hidden else ""})'


def safe_symbol_name(ref): return re.sub(r'[^A-Za-z0-9_]','_',ref)


def library_symbol(c):
    ref,base=c['ref'],safe_symbol_name(c['ref']); count=len(c['pin_names']); half=math.ceil(count/2); body_h=max(7.62,(half-1)*2.54+5.08)
    lines=[f'    (symbol "Reconstruction:{base}"','      (pin_names (offset 0.8))','      (exclude_from_sim no) (in_bom yes) (on_board yes)',f'      (property "Reference" "{re.sub(r"[0-9#]+","",ref) or ref}" (at 0 {-body_h/2-2:.2f} 0) {effects()})',f'      (property "Value" "{c["value"]}" (at 0 {body_h/2+2:.2f} 0) {effects()})',f'      (property "Footprint" "Reconstruction:{c["kind"]}_{count}P" (at 0 0 0) {effects(True)})',f'      (property "Datasheet" "~" (at 0 0 0) {effects(True)})',f'      (property "Description" "{c["value"]}" (at 0 0 0) {effects(True)})',f'      (symbol "{base}_0_1" (rectangle (start -7.62 {-body_h/2:.2f}) (end 7.62 {body_h/2:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))',f'      (symbol "{base}_1_1"']
    for pin,(name,ptype) in enumerate(zip(c['pin_names'],c['pin_types']),1):
        left=pin<=half; row=pin-1 if left else pin-half-1; y=-((half-1)*2.54)/2+row*2.54; x,angle=(-10.16,0) if left else (10.16,180)
        lines.append(f'        (pin {ptype} line (at {x:.2f} {y:.2f} {angle}) (length 2.54) (name "{name}" {effects()}) (number "{pin}" {effects()}))')
    lines += ['      )','      (embedded_fonts no)','    )']; return '\n'.join(lines)


grid=[("J2",25,30),("SW7",55,30),("U1",85,30),("C1",115,30),("C2",145,30),("C3",175,30),("J3",215,30),("SW6",245,30),("C4",275,30),("C5",305,30),("J9",335,30),("J1",170,100),("J5",25,85),("J10",315,85),("R3",275,85),("R4",275,105),("J4",25,150),("R1",55,150),("J6",90,150),("R5",120,142),("R6",120,158),("J7",160,150),("R7",190,142),("R8",190,158),("J8",230,150),("R9",260,142),("R10",260,158),("SW1",25,205),("SW2",55,205),("SW3",85,205),("SW4",115,205),("SW5",145,205),("R2",220,205),("R11",250,205),("Q1",285,205),("BZ1",320,205)]
# KiCad's default schematic connection grid is 50 mil (1.27 mm).  Symbols,
# pin endpoints, wires, and labels must share that grid for native ERC to
# recognize the generated connections.
schematic_positions={ref:(round(x/1.27)*1.27, round(y/1.27)*1.27) for ref,x,y in grid}; root_uuid=uid('schematic-root')
sch=['(kicad_sch','  (version 20250114)','  (generator "reconstruction_generator")','  (generator_version "2.0")',f'  (uuid "{root_uuid}")','  (paper "A3")','  (title_block (title "STM32 Fall Detection — Reconstructed Final Design") (rev "2.0") (company "Independent undergraduate project reconstruction") (comment 1 "Not Fabrication-Validated") (comment 2 "Final physical prototype governs placement; firmware governs confirmed GPIO"))','  (lib_symbols']
for c in components: sch.append(library_symbol(c))
sch.append('  )')
sch.append(f'  (text "{LABEL}" (exclude_from_sim no) (at 20 15 0) {effects()} (uuid "{uid("sch-title")}"))')
sch.append(f'  (text "DNP pull-ups are optional because photographed breakout revisions may already contain them." (exclude_from_sim no) (at 20 20 0) {effects()} (uuid "{uid("sch-note")}"))')
for c in components:
    ref=c['ref']; x,y=schematic_positions[ref]; count=len(c['pin_names']); half=math.ceil(count/2); sym_uuid=uid('sch-symbol-'+ref)
    sch += ['  (symbol',f'    (lib_id "Reconstruction:{safe_symbol_name(ref)}")',f'    (at {x} {y} 0)','    (unit 1)','    (exclude_from_sim no) (in_bom yes) (on_board yes)',f'    (dnp {"yes" if c["dnp"] else "no"})',f'    (uuid "{sym_uuid}")',f'    (property "Reference" "{ref}" (at {x} {y-8} 0) {effects()})',f'    (property "Value" "{c["value"]}" (at {x} {y+8} 0) {effects()})',f'    (property "Footprint" "Reconstruction:{c["kind"]}_{count}P" (at {x} {y} 0) {effects(True)})',f'    (property "Datasheet" "~" (at {x} {y} 0) {effects(True)})',f'    (property "Description" "{c["value"]}" (at {x} {y} 0) {effects(True)})']
    for pin in range(1,count+1): sch.append(f'    (pin "{pin}" (uuid "{uid(f"sch-pin-{ref}-{pin}")}"))')
    sch += [f'    (instances (project "{PROJECT}" (path "/{root_uuid}" (reference "{ref}") (unit 1))))','  )']
    for pin in range(1,count+1):
        left=pin<=half; row=pin-1 if left else pin-half-1; py=y-((half-1)*2.54)/2+row*2.54; px=x-10.16 if left else x+10.16; outer=px-3.81 if left else px+3.81; token=f'{ref}.{pin}'; net=padnet.get(token)
        if net:
            sch.append(f'  (wire (pts (xy {px:.3f} {py:.3f}) (xy {outer:.3f} {py:.3f})) (stroke (width 0) (type default)) (uuid "{uid("wire-"+token)}"))')
            sch.append(f'  (label "{net}" (at {outer:.3f} {py:.3f} 0) {effects(False,"right bottom" if left else "left bottom")} (uuid "{uid("label-"+token)}"))')
        else: sch.append(f'  (no_connect (at {px:.3f} {py:.3f}) (uuid "{uid("nc-"+token)}"))')
sch += ['  (sheet_instances (path "/" (page "1")))','  (embedded_fonts no)',')']
(OUT/f'{PROJECT}.kicad_sch').write_text('\n'.join(sch)+'\n')

netxml=[f'(export (version "E") (design (source "{PROJECT}.kicad_sch") (date "2026-11-10") (tool "reconstruction-generator-2.0")) (components']
for c in components: netxml.append(f' (comp (ref "{c["ref"]}") (value "{c["value"]}") (footprint "Reconstruction:{c["kind"]}_{len(c["pin_names"])}P"))')
netxml.append(') (nets')
for net,idx in net_index.items():
    netxml.append(f' (net (code "{idx}") (name "{net}")')
    for token in nets[net]: ref,pin=token.split('.'); netxml.append(f'  (node (ref "{ref}") (pin "{pin}"))')
    netxml.append(' )')
netxml.append('))'); (OUT/f'{PROJECT}.net').write_text('\n'.join(netxml)+'\n')
pad_geometry=[]
for c in components:
    smd=c['kind']=='resistor_smd'
    radius=0.6 if smd else (1.05 if c['kind'] in {'power','switch','buzzer','capacitor_large'} else 0.9)
    for pin in range(1,len(c['pin_names'])+1):
        x,y=abs_pad(c['ref'],pin); token=f'{c["ref"]}.{pin}'
        pad_geometry.append({'pad':token,'x':x,'y':y,'net':padnet.get(token),'layers':[0] if smd else [0,1],'radius':radius})
copper={'tracks':[{'net':net,'a':a,'b':b,'layer':layer,'width':width} for net,a,b,layer,width in tracks],'vias':[{'net':net,'x':p[0],'y':p[1],'diameter':1.0,'drill':0.5} for net,p in vias],'pads':pad_geometry}
(OUT/'connectivity.json').write_text(json.dumps({"label":LABEL,"board_mm":[W,H],"nets":nets,"route_failures":route_failures,"tracks":len(tracks),"vias":len(vias),"components":[{"ref":c['ref'],"value":c['value'],"x_mm":c['x'],"y_mm":c['y'],"category":c['kind'],"pads":len(c['pin_names']),"pin_names":c['pin_names'],"dnp":c['dnp']} for c in components],"copper":copper},indent=2)+'\n')

COL={"power":"#e6a23c","controller":"#2563a6","sensor":"#39a578","module":"#647a9d","button":"#c2c9d1","switch":"#9477b8","resistor":"#d7b967","resistor_smd":"#d7b967","transistor":"#90b4c6","buzzer":"#b96c5e","regulator":"#5670a8","capacitor":"#556b73","capacitor_large":"#556b73"}
def xml_escape(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def render_svg(back=False):
    scale,margin=9.7,55; X=lambda x:margin+x*scale; Y=lambda y:margin+y*scale; s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="900" viewBox="0 0 1150 900">','<rect width="100%" height="100%" fill="#e9edf0"/>',f'<rect x="{X(0)}" y="{Y(0)}" width="{W*scale}" height="{H*scale}" rx="10" fill="#176048" stroke="#102f28" stroke-width="5"/>']
    layer=1 if back else 0
    for net,a,b,l,width in tracks:
        if l==layer: s.append(f'<line x1="{X(a[0])}" y1="{Y(a[1])}" x2="{X(b[0])}" y2="{Y(b[1])}" stroke="{"#ef8f5a" if net in {"+5V","3V3","SIM_VBAT"} else "#f0c75e"}" stroke-width="{max(2,width*scale)}" stroke-linecap="round" opacity=".85"/>')
    for net,p in vias: s.append(f'<circle cx="{X(p[0])}" cy="{Y(p[1])}" r="4" fill="#c9973c" stroke="#f4d594"/>')
    for c in components:
        fw,fh=SIZES[c['kind']]; color='#154d3b' if back else COL.get(c['kind'],'#728096'); s.append(f'<rect x="{X(c["x"]-fw/2)}" y="{Y(c["y"]-fh/2)}" width="{fw*scale}" height="{fh*scale}" rx="3" fill="{color}" fill-opacity=".92" stroke="#ecf4ef" stroke-width="1.2"/>'); s.append(f'<text x="{X(c["x"])}" y="{Y(c["y"])}" text-anchor="middle" font-family="Arial" font-size="9" fill="#fff">{xml_escape(c["ref"])}</text>')
        for pin in range(1,len(c['pin_names'])+1): px,py=abs_pad(c['ref'],pin); s.append(f'<circle cx="{X(px)}" cy="{Y(py)}" r="3.5" fill="#c89c47" stroke="#f4d594"/>')
    s.append(f'<text x="30" y="30" font-family="Arial" font-size="20" font-weight="bold" fill="#213442">{"BACK COPPER / GND PLANE" if back else "FRONT COPPER / COMPONENT PLACEMENT"} · ENGINEERING PREVIEW</text>'); s.append('</svg>'); return '\n'.join(s)
for name,back in [('pcb-front',False),('pcb-back',True)]:
    svg=OUT/f'{name}.svg'; svg.write_text(render_svg(back))
    if subprocess.run(['which','rsvg-convert'],capture_output=True).returncode==0: subprocess.run(['rsvg-convert','-o',str(OUT/f'{name}.png'),str(svg)],check=True)
print(f'Wrote {OUT}; routed segments={len(tracks)}, vias={len(vias)}, failures={len(route_failures)}')
for failure in route_failures: print('UNROUTED',failure)
