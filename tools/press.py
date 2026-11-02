#!/usr/bin/env python3
"""press.py button[:seconds] ...: press buttons of the game in RPCS3, one after the other (cross circle
square triangle l1 r1 l2 r2 select start l3 r3 up down left right, the sticks lx- lx+ ly- ly+ rx- rx+
ry- ry+, or wait:seconds). Stick up is ly-. Words joined by a comma go together: ly-,cross:0.5 holds
the stick and the button for 0.5 seconds.

The buttons are written into the running game (tools/peek.py), where the mod's pad hook hands them
on as if from the pad, so nothing outside RPCS3 sees them: no device, no keys, no focus."""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mods.game import STATE

PEEK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "peek.py")
BUTTONS, STICKS = STATE + 0x418, STATE + 0x41C
DIGITAL_1 = dict(select=1, l3=2, r3=4, start=8, up=0x10, right=0x20, down=0x40, left=0x80)
DIGITAL_2 = dict(l2=1, r2=2, l1=4, r1=8, triangle=0x10, circle=0x20, cross=0x40, square=0x80)
AXES = dict(rx=0, ry=1, lx=2, ly=3)


def write(buttons, sticks):
    words = f"w {BUTTONS:x} {struct.pack('>I', buttons).hex()}, w {STICKS:x} {bytes(sticks).hex()}"
    subprocess.run([sys.executable, PEEK, words], check=True, stdout=subprocess.DEVNULL)


def main():
    for word in sys.argv[1:]:
        name, _, held = word.partition(":")
        held = float(held or 0.15)
        if name == "wait":
            time.sleep(held)
            continue
        buttons, sticks = 0, [0x80] * 4
        for part in name.split(","):
            if part in DIGITAL_1:
                buttons |= DIGITAL_1[part] << 16
            elif part in DIGITAL_2:
                buttons |= DIGITAL_2[part]
            else:
                sticks[AXES[part[:2]]] = 0xFF if part[2] == "+" else 0
        write(buttons, sticks)
        time.sleep(held)
        write(0, [0, 0, 0, 0])
        time.sleep(0.2)


if __name__ == "__main__":
    main()
