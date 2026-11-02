#!/usr/bin/env python3
"""inputprofile.py: writes RPCS3's input profile "Backport" for sessions without anyone at the pad.

Player 1 on the keyboard, so the game sees a pad connected, and everyone else on nothing, from a copy
of the user's Default.yml, which is left alone. No keys are ever sent: tools/press.py writes the
buttons into the game (mods/portal.py, pt_pad), so nothing the rest of the system can see is involved.
A uinput pad would be a device for every program on the machine.
"""
import os
import re

GLOBAL = os.path.expanduser("~/.config/rpcs3/input_configs/global")
NAME = "Backport"


def write():
    out, player = [], 0
    for line in open(os.path.join(GLOBAL, "Default.yml")):
        head = re.match(r"^Player (\d) Input:", line)
        if head:
            player = int(head.group(1))
        elif re.match(r"^\S", line):
            player = 0
        if player and re.match(r"^  (Handler|Device):", line):
            key = line.split(":")[0].strip()
            line = f"  {key}: {'Keyboard' if player == 1 else chr(34) + 'Null' + chr(34)}\n"
        out.append(line)
    with open(os.path.join(GLOBAL, NAME + ".yml"), "w") as f:
        f.writelines(out)


if __name__ == "__main__":
    write()
    print(f"wrote {NAME}.yml")
