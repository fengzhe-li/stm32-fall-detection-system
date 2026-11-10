#!/usr/bin/env python3
"""Generate the editable KiCad reconstruction and portable board previews."""
from pathlib import Path
import json, math, uuid

ROOT = Path(__file__).parent
OUT = ROOT / "Reconstructed_Final_Design"
OUT.mkdir(exist_ok=True)
uid = lambda: str(uuid.uuid4())

# Netlist is intentionally explicit: module-specific pin numbering remains an
# open item where the photographed breakout revisions cannot be identified.
nets = {
 "GND": ["J1.19", "J1.20", "J1.39", "J2.2", "J3.2", "J4.2", "J5.2", "J6.2", "J7.2", "J8.2", "J9.2", "J10.2", "SW1.2", "SW2.2", "SW3.2", "SW4.2", "SW5.2", "Q1.1", "U1.1", "C1.2", "C2.2", "C3.2"],
 "+5V": ["SW7.1", "BZ1.1", "U1.3", "C1.1"],
 "+5V_INPUT": ["J2.1", "SW7.2"],
 "SIM_VBAT": ["SW6.1", "J9.1"],
 "SIM_VBAT_INPUT": ["J3.1", "SW6.2"],
 "3V3": ["J1.18", "J1.40", "J4.1", "J5.1", "J6.1", "J7.1", "J8.1", "J10.1", "R1.2", "U1.2", "C2.1", "C3.1"],
 "GPS_TX_TO_MCU_RX_PB11": ["J1.16", "J5.3"],
 "GPS_RX_FROM_MCU_TX_PB10": ["J1.15", "J1.38", "J5.4"],
 "GSM_TX_TO_MCU_RX_PA10": ["J1.27", "J10.3"],
 "GSM_RX_FROM_MCU_TX_PA9": ["J1.26", "J10.4"],
 "ACCEL_SCL_PA6": ["J1.11", "J6.3"],
 "ACCEL_SDA_PA7": ["J1.12", "J6.4"],
 "MAX_SCL_PB1": ["J1.14", "J7.3"],
 "MAX_SDA_PB0": ["J1.13", "J7.4"],
 "OLED_SCL_PB6": ["J1.34", "J8.3"],
 "OLED_SDA_PB7": ["J1.35", "J8.4"],
 "TEMP_DQ_PA11": ["J1.28", "J4.3", "R1.1"],
 "BUZZER_PC13": ["J1.2", "R2.1"],
 "BUZZER_LOW_SIDE": ["Q1.2", "BZ1.2"],
 "BTN_MODE_PB12": ["J1.21", "SW1.1"],
 "BTN_UP_PB13": ["J1.22", "SW2.1"],
 "BTN_DOWN_PB14": ["J1.23", "SW3.1"],
 "BTN_NEXT_PB15": ["J1.24", "SW4.1"],
 "BTN_HELP_PA8": ["J1.25", "SW5.1"],
 "BUZZER_BASE": ["R2.2", "Q1.3"],
}

# Module footprints are connectorized representations of prebuilt boards.
# Physical arrangement follows the photographed white carrier board.
W,H=104,82
components = [
 ("J1","Blue Pill socket, 2x20, 2.54 mm",55,39,"controller",40),
 ("J2","Main 5 V DC input",7,8,"power",2),
 ("J3","SIM800 external VBAT input (nominal 4 V)",97,8,"power",2),
 ("J4","DS18B20 3-pin module",14,36,"sensor",3),
 ("J5","VK2828U7G5LF GPS UART module",23,17,"module",4),
 ("J6","ADXL345 breakout",59,73.5,"sensor",4),
 ("J7","MAX30102 breakout",35,73.5,"sensor",4),
 ("J8","0.96 inch OLED I2C module",16,56,"module",4),
 ("J9","SIM800C breakout power",99,40,"power",2),
 ("J10","SIM800 UART / status header",85,25,"module",4),
 ("SW1","Mode",72,59,"button",2),("SW2","Up",82,59,"button",2),
 ("SW3","Down",72,69,"button",2),("SW4","Next",82,69,"button",2),
 ("SW5","Help",92,69,"button",2),
 ("SW6","GSM VBAT switch",98.5,49,"switch",2),("SW7","Main power switch",8,19,"switch",2),
 ("R1","10k DS18B20 pull-up",30,36,"resistor",2),
 ("Q1","S8050 low-side buzzer driver",89,50,"transistor",3),
 ("R2","1k base resistor",90,45,"resistor",2),
 ("BZ1","5 V active buzzer",96,59,"buzzer",2),
 ("U1","AMS1117-3.3 regulator module",49,8,"regulator",3),
 ("C1","10 uF input capacitor",40.5,8,"capacitor",2),
 ("C2","10 uF output capacitor",57,8,"capacitor",2),
 ("C3","100 nF output bypass",64,8,"capacitor",2),
]

def xml_escape(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def footprint(ref,val,x,y,kind,count,net_by_pad):
    sizes={'controller':(25.4,53.3),'power':(10,8),'sensor':(18,14),'module':(22,18),'button':(6,6),'switch':(8,6),'resistor':(7,4),'transistor':(5,5),'buzzer':(12,12),'programming':(9,7),'regulator':(10,8),'capacitor':(5,4)}
    fw,fh=sizes.get(kind,(10,8))
    lines=[f'  (footprint "Reconstruction:{kind}_{count}P" (layer "F.Cu") (uuid "{uid()}") (at {x} {y})',
           f'    (property "Reference" "{ref}" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
           f'    (property "Value" "{val}" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
           '    (attr through_hole)',
           f'    (fp_rect (start {-fw/2:.2f} {-fh/2:.2f}) (end {fw/2:.2f} {fh/2:.2f}) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))',
           f'    (fp_rect (start {-fw/2:.2f} {-fh/2:.2f}) (end {fw/2:.2f} {fh/2:.2f}) (stroke (width 0.05) (type default)) (fill none) (layer "F.Fab"))']
    for p in range(1,count+1):
        px=(-7.62 if p<=20 else 7.62) if count==40 else (0 if count>2 else (-1.27 if p%2 else 1.27))
        py=((p-1)%20)*2.54-24.13 if count==40 else (p-1)*2.54
        name=net_by_pad.get(f'{ref}.{p}')
        nidx=next((i for i,(n,_) in enumerate(nets.items(),1) if n==name),0) if name else 0
        lines.append(f'    (pad "{p}" thru_hole circle (at {px:.2f} {py:.2f}) (size 1.7 1.7) (drill 0.9) (layers "*.Cu" "*.Mask")'+(f' (net {nidx} "{name}")' if name else '')+f' (uuid "{uid()}"))')
    lines.append('  )')
    return '\n'.join(lines)

padnet={p:n for n,ps in nets.items() for p in ps}
board=['(kicad_pcb (version 20250114) (generator "pcbnew") (uuid "'+uid()+'")','  (general (thickness 1.6))','  (paper "A4")',
 '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user) (33 "F.Adhes" user) (34 "F.Paste" user) (35 "B.Paste" user) (36 "F.SilkS" user) (37 "B.SilkS" user) (38 "F.Mask" user) (39 "B.Mask" user) (44 "Edge.Cuts" user))',
 '  (setup (pad_to_mask_clearance 0))']
for i,n in enumerate(nets,1): board.append(f'  (net {i} "{n}")')
for c in components: board.append(footprint(*c,padnet))
board += [f'  (gr_rect (start 0 0) (end {W} {H}) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))','  (gr_text "RECONSTRUCTED FINAL DESIGN / NOT FABRICATION-VALIDATED" (at 52 3) (layer "F.SilkS") (effects (font (size 1.4 1.4) (thickness 0.22))))','  (gr_text "STM32 FALL DETECTION + HEALTH MONITOR" (at 52 79) (layer "F.SilkS") (effects (font (size 1.4 1.4) (thickness 0.22))))',')']
(OUT/'FallDetection_Reconstructed.kicad_pcb').write_text('\n'.join(board)+'\n')
(OUT/'FallDetection_Reconstructed.kicad_pro').write_text('{}\n')

# Human-readable editable sheet notes plus an explicit connectivity netlist.
sch=['(kicad_sch (version 20250114) (generator "eeschema")','  (uuid '+uid()+')','  (paper "A3")','  (title_block (title "Reconstructed Final Design Based on the Final Physical Prototype") (rev "1.0") (comment 1 "Not Fabrication-Validated"))']
sch.append('  (text "STM32 FALL DETECTION + HEALTH MONITOR — RECONSTRUCTED DESIGN" (at 100 20 0) (effects (font (size 2.5 2.5) (thickness 0.35))))')
sch.append('  (text "Editable connectivity authority: accompanying .net file and PCB pad nets. Module connectors represent carrier-board sockets; exact breakout revisions remain unverified." (at 100 25 0) (effects (font (size 1.2 1.2) (thickness 0.18))))')
for i,(net,pads) in enumerate(nets.items()):
    sch.append(f'  (text "{net}: {", ".join(pads)}" (at 20 {35+i*5} 0) (effects (font (size 1.05 1.05) (thickness 0.15))))')
sch.append(')')
(OUT/'FallDetection_Reconstructed.kicad_sch').write_text('\n'.join(sch)+'\n')

netxml=['(export (version "E") (design (source "FallDetection_Reconstructed.kicad_sch") (date "2026-11-10") (tool "reconstruction-generator")) (components']
for ref,val,*_ in components: netxml.append(f' (comp (ref "{ref}") (value "{val}"))')
netxml.append(') (nets')
for i,(n,ps) in enumerate(nets.items(),1):
    netxml.append(f' (net (code "{i}") (name "{n}")')
    for pp in ps:
        ref,pin=pp.split('.')
        netxml.append(f'  (node (ref "{ref}") (pin "{pin}"))')
    netxml.append(' )')
netxml.append('))')
(OUT/'FallDetection_Reconstructed.net').write_text('\n'.join(netxml)+'\n')
(OUT/'connectivity.json').write_text(json.dumps({"label":"Reconstructed Design Based on the Final Physical Prototype — Not Fabrication-Validated","nets":nets,"components":[{"ref":c[0],"value":c[1],"x_mm":c[2],"y_mm":c[3],"category":c[4],"pads":c[5]} for c in components]},indent=2)+'\n')

# Photo-style engineering renders. Geometry is shared with the KiCad placements.
COL={"power":"#e6a23c","controller":"#2563a6","sensor":"#39a578","module":"#647a9d","button":"#c2c9d1","resistor":"#d7b967","transistor":"#90b4c6","buzzer":"#b96c5e","programming":"#7663a5"}
SIZES={'controller':(25.4,53.3),'power':(10,8),'sensor':(18,14),'module':(22,18),'button':(6,6),'switch':(8,6),'resistor':(7,4),'transistor':(5,5),'buzzer':(12,12),'programming':(9,7),'regulator':(10,8),'capacitor':(5,4)}
def render_svg(back=False,iso=False):
    sw,sh=(1150,900) if not iso else (1200,900); scale=9.7
    def X(x): return 55+x*scale
    def Y(y): return 55+y*scale
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}" viewBox="0 0 {sw} {sh}">','<defs><linearGradient id="board" x2="0" y2="1"><stop stop-color="#257b61"/><stop offset="1" stop-color="#145744"/></linearGradient><filter id="shadow"><feDropShadow dx="2" dy="3" stdDeviation="3" flood-opacity=".35"/></filter></defs>','<rect width="100%" height="100%" fill="#e9edf0"/>']
    if iso:
        s += ['<polygon points="190,220 860,130 1045,245 380,340" fill="#2a8d69" stroke="#102f28" stroke-width="5" filter="url(#shadow)"/>','<polygon points="380,340 1045,245 1045,720 380,815" fill="#176048" stroke="#102f28" stroke-width="5"/>','<polygon points="190,220 380,340 380,815 190,695" fill="#1e7458" stroke="#102f28" stroke-width="5"/>']
        s += ['<g font-family="Arial" font-size="26" fill="#e8f4ee"><text x="430" y="390">BLUE PILL / STM32F103C8T6</text><text x="230" y="490">GPS + OLED</text><text x="690" y="570">SIM800C</text><text x="465" y="690">ADXL345 · MAX30102 · BUTTONS</text></g>']
    else:
        s += [f'<rect x="{X(0)}" y="{Y(0)}" width="{W*scale}" height="{H*scale}" rx="12" fill="url(#board)" stroke="#123f32" stroke-width="6"/>']
        s.append(f'<text x="{X(52)}" y="{Y(3)}" text-anchor="middle" font-family="Arial" font-size="13" fill="#fff">RECONSTRUCTED FINAL DESIGN · NOT FABRICATION-VALIDATED</text>')
        names={'J1':'STM32F103C8T6','J2':'MAIN 5V IN','J3':'MODEM VBAT','J4':'DS18B20','J5':'VK2828U7 GPS','J6':'ADXL345','J7':'MAX30102','J8':'0.96 OLED','J9':'SIM800 PWR','J10':'SIM800C','J11':'GPS AUX','J12':'SWD','SW1':'MODE','SW2':'UP','SW3':'DOWN','SW4':'NEXT','SW5':'HELP','SW6':'GSM PWR','SW7':'MAIN PWR','R1':'10K','R2':'1K','Q1':'S8050','BZ1':'BUZZER'}
        for ref,val,x,y,kind,count in components:
            cx,cy=X(x),Y(y); fw,fh=SIZES[kind]; w,h=fw*scale,fh*scale
            color='#154d3b' if back else COL.get(kind,'#728096')
            label=ref if back else names.get(ref,ref)
            s.append(f'<g filter="url(#shadow)"><rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="4" fill="{color}" stroke="#ecf4ef" stroke-width="1.4"/><text x="{cx}" y="{cy-1}" text-anchor="middle" font-family="Arial" font-size="10" fill="#fff">{xml_escape(label)}</text><text x="{cx}" y="{cy+11}" text-anchor="middle" font-family="Arial" font-size="8" fill="#dce9e2">{xml_escape(ref)}</text></g>')
            if back:
                n=count
                for p in range(1,n+1):
                    px=(-7.62 if p<=20 else 7.62) if count==40 else (0 if count>2 else (-1.27 if p%2 else 1.27))
                    py=((p-1)%20)*2.54-24.13 if count==40 else (p-1)*2.54
                    s.append(f'<circle cx="{X(x+px)}" cy="{Y(y+py)}" r="4.4" fill="#c89c47" stroke="#f4d594" stroke-width="1"/><circle cx="{X(x+px)}" cy="{Y(y+py)}" r="1.7" fill="#26342e"/>')
    title='Back face · no copper routing' if back else ('Isometric assembly preview' if iso else 'Front placement · module outlines approximate')
    s += [f'<text x="30" y="30" font-family="Arial" font-size="20" font-weight="bold" fill="#213442">{title}</text>','</svg>']
    return '\n'.join(s)
for name,back,iso in [('pcb-front.svg',False,False),('pcb-back.svg',True,False),('pcb-3d.svg',False,True)]: (OUT/name).write_text(render_svg(back,iso))
import subprocess
for fn in ['pcb-front','pcb-back','pcb-3d']:
 subprocess.run(['rsvg-convert','-o',str(OUT/(fn+'.png')),str(OUT/(fn+'.svg'))],check=True)
print('Wrote',OUT)
