#!/usr/bin/env python3
"""fullsave.py [--source B] [--target C] [--bolts N]: a test save with all planets and weapons.

Copies a save slot into a new one, changing only the copy: every planet on the map, every named
item owned with full ammunition, and a lot of bolts. Run it with RPCS3 open or closed: it refuses to
write to a slot that exists, so nothing of yours can be overwritten. NOTES.md (Saves) has the format.

Story progress stays as it was in the source: this is a test save, not a finished game.
"""
import argparse
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppu import Elf, RC2_ELF  # noqa: E402

SAVES = os.path.expanduser("~/.config/rpcs3/dev_hdd0/home/00000001/savedata")
PREFIX = "NPEA00386_RC2_SAVEDATA_"
BLOCK = 0x10                       # the first chunk of the global block
BOLTS, AMMO, OWNED, EVER, QUICK, PLANETS, MAP = 4, 9, 0xA, 0xB, 0xD, 0xE, 0x14    # chunk ids
LEVELS = 0x1C
ITEMS = 0x38
ON_MAP = [*range(1, 0x15), 0x18]   # the levels 0xb722d4, the game's unlock, puts on the map
ITEM_TABLE, ITEM_SIZE, ITEM_FIRST = 0x13222B0, 0xD0, 0xA    # item 0 is entry 0xa
ITEM_NAME, ITEM_MAX = 4, 0x4A      # u16: text id, the most ammunition
NOT_ITEMS = {0x34}                 # the name of 0x14 again, and in no list of the game's
QUICK_SELECT = (0x1E, 0x2A, 0x09, 0x1D, 0x16, 0x17, 0x18, 0x1A)    # 0x09: the mod's Portal Gun


def chunks(data):
    """id -> (place of its data, size), up to the block's end mark."""
    out, at = {}, BLOCK
    while True:
        chunk, size = struct.unpack_from(">II", data, at)
        if chunk == 0xFFFFFFFF:
            return out
        if size > len(data) - at or chunk in out:
            sys.exit(f"not a save this tool knows: chunk {chunk:#x} of {size:#x} bytes at {at:#x}")
        out[chunk] = (at + 8, size)
        at = (at + 8 + size + 3) & ~3


def items():
    """item -> the most ammunition it can hold, for the items that have a name."""
    elf, out = Elf(RC2_ELF), {}
    for item in range(ITEMS):
        entry = elf.read(ITEM_TABLE + (item + ITEM_FIRST) * ITEM_SIZE, ITEM_SIZE)
        if item not in NOT_ITEMS and struct.unpack_from(">H", entry, ITEM_NAME)[0]:
            out[item] = struct.unpack_from(">H", entry, ITEM_MAX)[0]
    return out


def change(data, bolts):
    data = bytearray(data)
    found = chunks(data)
    expected = {BOLTS: 8, AMMO: ITEMS * 4, OWNED: ITEMS, EVER: ITEMS, QUICK: 0x20, PLANETS: LEVELS, MAP: LEVELS * 4}
    for chunk, size in expected.items():
        if chunk not in found or found[chunk][1] != size:
            sys.exit(f"chunk {chunk:#x} is not {size:#x} bytes here: not a save this tool knows")
    struct.pack_into(">I", data, found[BOLTS][0], bolts)      # the word behind it stays: not known
    for item, ammunition in items().items():
        data[found[OWNED][0] + item] = data[found[EVER][0] + item] = 1
        struct.pack_into(">I", data, found[AMMO][0] + item * 4, ammunition)
    struct.pack_into(">8I", data, found[QUICK][0], *QUICK_SELECT)
    for level in range(1, LEVELS - 1):
        data[found[PLANETS][0] + level] = 1
    at = found[MAP][0]
    listed = [v for v in struct.unpack_from(f">{LEVELS}I", data, at) if v]
    listed += [level for level in ON_MAP if level not in listed]
    struct.pack_into(f">{LEVELS}I", data, at, *listed, *[0] * (LEVELS - len(listed)))
    return bytes(data)


def param(data, directory, bolts):
    """PARAM.SFO with the new slot's name and the text the save list shows."""
    data = bytearray(data)
    keys, values, count = struct.unpack_from("<III", data, 8)
    for n in range(count):
        at = 0x14 + n * 16
        name, _, used, room, place = struct.unpack_from("<HHIII", data, at)
        key = bytes(data[keys + name:data.index(0, keys + name)])
        if key == b"SAVEDATA_DIRECTORY":
            text = directory.encode() + b"\0"
        elif key == b"DETAIL":
            old = bytes(data[values + place:values + place + used]).split(b"\n")[0]
            text = old + f"\nTEST SAVE: all planets, all weapons\nBolts: {bolts}".encode() + b"\0"
        else:
            continue
        if len(text) > room:
            sys.exit(f"{key.decode()} does not fit")
        data[values + place:values + place + room] = text.ljust(room, b"\0")
        struct.pack_into("<I", data, at + 4, len(text))
    return bytes(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", default="B", help="the slot to start from (default B)")
    ap.add_argument("--target", default="C", help="the new slot (default C); it must not exist")
    ap.add_argument("--bolts", type=int, default=9999999)
    args = ap.parse_args()
    source, directory = os.path.join(SAVES, PREFIX + args.source), PREFIX + args.target
    target = os.path.join(SAVES, directory)
    if os.path.exists(target):
        sys.exit(f"{target} exists: nothing written. Move it away first if you want it rebuilt.")
    with open(os.path.join(source, "USR-DATA"), "rb") as f:
        save = change(f.read(), args.bolts)
    with open(os.path.join(source, "PARAM.SFO"), "rb") as f:
        sfo = param(f.read(), directory, args.bolts)
    work = target + ".new"                 # the game lists the folders: it appears whole or not at all
    shutil.rmtree(work, ignore_errors=True)
    os.mkdir(work)
    for name in ("ICON0.PNG", "PIC1.PNG"):
        shutil.copyfile(os.path.join(source, name), os.path.join(work, name))
    for name, content in (("USR-DATA", save), ("PARAM.SFO", sfo)):
        with open(os.path.join(work, name), "wb") as f:
            f.write(content)
    os.rename(work, target)
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
