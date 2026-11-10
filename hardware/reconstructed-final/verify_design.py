#!/usr/bin/env python3
"""Static connectivity and geometry checks for the generated reconstruction."""
from pathlib import Path
import json, re, sys
root=Path(__file__).parent/'Reconstructed_Final_Design'
d=json.loads((root/'connectivity.json').read_text())
errors=[]; warnings=[]
refs=[c['ref'] for c in d['components']]
if len(refs)!=len(set(refs)): errors.append('duplicate component references')
allpads=set()
for c in d['components']:
    for p in range(1,c['pads']+1): allpads.add(f"{c['ref']}.{p}")
seen={}
for n,pads in d['nets'].items():
    if len(pads)<2: warnings.append(f'{n}: only {len(pads)} pad(s)')
    for p in pads:
        if p not in allpads: errors.append(f'{n}: references missing pad {p}')
        if p in seen: errors.append(f'{p} assigned to both {seen[p]} and {n}')
        seen[p]=n
for required in ['GND','+5V','3V3','SIM_VBAT','GPS_TX_TO_MCU_RX_PB11','ACCEL_SCL_PA6','ACCEL_SDA_PA7','MAX_SCL_PB1','MAX_SDA_PB0','OLED_SCL_PB6','OLED_SDA_PB7','TEMP_DQ_PA11','BUZZER_PC13']:
    if required not in d['nets']: errors.append('missing required net '+required)
if d.get('route_failures'): errors.append('autorouter failures: '+', '.join(d['route_failures']))
if 'J1.38' in d['nets'].get('GPS_RX_FROM_MCU_TX_PB10',[]): errors.append('Blue Pill pin 38 incorrectly tied to PB10')
if any('J1.38' in pads for pads in d['nets'].values()): errors.append('Blue Pill 5 V pin 38 must remain unconnected in this 3.3 V power architecture')
sizes={'controller':(25.4,53.3),'power':(10,8),'sensor':(18,14),'temp_sensor':(12,8),'module':(22,16),'button':(7,7),'switch':(9,6),'resistor':(9,4),'resistor_smd':(2.4,1.4),'transistor':(6,5),'buzzer':(12,12),'regulator':(11,8),'capacitor':(5,5),'capacitor_large':(11,11)}
boxes=[]
for c in d['components']:
    w,h=sizes.get(c['category'],(8,6)); x,y=c['x_mm'],c['y_mm']
    if x-w/2<0 or y-h/2<0 or x+w/2>104 or y+h/2>82: errors.append(f"{c['ref']}: estimated body outside 104x82 mm outline")
    boxes.append((c['ref'],x-w/2,y-h/2,x+w/2,y+h/2))
for i,a in enumerate(boxes):
    for b in boxes[i+1:]:
        if min(a[3],b[3])-max(a[1],b[1])>0.3 and min(a[4],b[4])-max(a[2],b[2])>0.3:
            warnings.append(f'approximate body overlap: {a[0]} with {b[0]}')
for f in ['FallDetection_Reconstructed.kicad_pcb','FallDetection_Reconstructed.kicad_sch']:
    s=(root/f).read_text(); depth=0; instr=False; esc=False
    for ch in s:
        if instr:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': instr=False
        else:
            if ch=='"': instr=True
            elif ch=='(': depth+=1
            elif ch==')': depth-=1
            if depth<0: errors.append(f'{f}: closing parenthesis before opening'); break
    if depth!=0 or instr: errors.append(f'{f}: unbalanced S-expression syntax')
pcb=(root/'FallDetection_Reconstructed.kicad_pcb').read_text()
sch=(root/'FallDetection_Reconstructed.kicad_sch').read_text()
if '(zone (net 1) (net_name "GND") (layer "B.Cu")' not in pcb: errors.append('missing B.Cu GND zone')
if pcb.count('(segment ') < 25: errors.append('insufficient routed copper segments')
for token in ['(lib_symbols','  (symbol','  (wire','  (label','  (no_connect']:
    if token not in sch: errors.append('schematic lacks '+token.strip())
for net,pads in d['nets'].items():
    if sch.count(f'(label "{net}"') != len(pads): errors.append(f'{net}: schematic label count does not match pad membership')
    if net != 'GND' and f'(net {list(d["nets"]).index(net)+1} "{net}")' not in pcb: errors.append(f'{net}: missing PCB net declaration')
if errors:
    print('FAIL'); print('\n'.join(errors)); sys.exit(1)
print('PASS: schematic symbols/wires/labels, PCB pad nets, routed copper, GND zone, geometry, pin-38 correction, and KiCad delimiters passed local structural checks.')
for w in warnings: print('WARN:',w)
print(f"Components: {len(refs)}; connected pads: {len(seen)}; nets: {len(d['nets'])}.")
