#!/usr/bin/env python3
"""Fill PCB copper zones in a validation copy using KiCad's supported API."""
from pathlib import Path
import argparse
import pcbnew


parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

board = pcbnew.LoadBoard(str(args.source))
if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
    raise SystemExit("KiCad zone filling failed")
pcbnew.SaveBoard(str(args.output), board)
print(f"Filled zones in validation copy: {args.output}")
