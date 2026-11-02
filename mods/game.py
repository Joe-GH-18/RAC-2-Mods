"""What the mods have in common: the game's functions and data, the room for new code and
state, the data segments, and the hook sites more than one mod uses.

Everything here is for Ratchet & Clank 2 HD, RC2.ppu.elf of the European Trilogy disc
(BCES01503). Findings and how far each is confirmed are in NOTES.md.
"""
import struct

GAME = "BCES01503"
ORIG_MD5 = "f4b36fb839e5dc77125846f398b7e082"     # the untouched, decrypted RC2.ppu.elf


def ha(v):
    """The upper half of an address for lis, to go with addi and lo()."""
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def pair(name, address):
    """The template fields NAME_HA and NAME_LO of an address that is not a constant of a module."""
    return {name + "_HA": ha(address), name + "_LO": lo(address)}


def floats(*values):
    return struct.pack(f">{len(values)}f", *values)


class Hook:
    """A game instruction that build.py replaces with a call (bl) of a mod's routine.

    site: its address. label: the routine. original: the function the instruction called, or the
    instruction word itself when it was no call; then the routine does what it did and returns.
    chain: the site is one that other mods hook too. Such a routine does not return or call the
    function itself: where it is done, at the label <label>_next, it has the line {CHAIN}, which
    becomes a branch to the next mod's routine for the site and, in the last one, to the function
    (or to the displaced instruction and back). The mods are chained in the order of mods.MODS.
    jump: the instruction becomes a jump (b) instead of a call, for sites in functions that do
    not save their return address. The routine does what the instruction did and jumps back to
    the one behind it itself.
    """

    def __init__(self, site, label, original, chain=False, jump=False):
        self.site, self.label, self.original, self.chain, self.jump = site, label, original, chain, jump


# Game data
HERO = 0x147F1E0           # +0x80 position, +0x2290 hero moby, +0x2294 state
PAD = 0x147A380            # the pad block
CAMERA = 0x146E280         # +0x140 position, +0x370 matrix (rows: view axis, left, up)
FRAME_COUNTER = 0x156B070  # frames since the level started
GAME_MODE = 0x156B064      # seen live: 3 in the pause menu, 0, 1 and 4 elsewhere; not the level (NOTES.md)
ITEM_TABLE = 0x13222B0     # 0xd0 bytes per item: +0x08 slot, +0x0c model count, +0x10/+0x14 classes

# The frame's draw (shared engine code, one copy of each)
GAME_LOOP = 0xB4C8E8
PRE_DRAW = 0xB0F908        # builds the frame's work; ends in the world's draw
BUILD_VIEW = 0xB05020      # the view matrices from CAMERA
BUILD_PROJECTION = 0xB05600
FOV = 0x1472130
SECOND_VIEW = 0xB09478     # the one place that draws a second view in a frame (see NOTES.md)

# Code: the mods' routines and constants go, one mod after the other, into the zero padding
# between the end of the R+X segment (0x12d6668) and 0x12e0000. A mod that no longer fits there
# goes behind the data of the segment FAR_CODE below, which is made executable for it; all of
# the game's code is within reach of a branch from there.
CAVE_START = 0x12D6700
SEG_END = 0x12E0000
# State: zero-initialised memory appended to the RW segment's bss (old end 0x1fd1090), read and
# written in a running game by tools/trace.py and tools/peek.py. Laid out by each mod.
STATE = 0x1FD1100
STATE_END = 0x1FD3100

# Data: what a mod embeds is loaded through the ELF's three unused PT_LOAD entries (program
# header index, address). Each takes the data of all mods one after the other, 16-byte aligned:
# "ro" is read-only, "rw" writable (flags 6), "rw2" writable with the flags 0x6600006. RPCS3 loads
# the system modules from 0x2000000 up, so nothing may be mapped there: all three share the 128 KB
# behind the state block, which also keeps code in "ro" within reach of the game's whole text.
SEGMENTS = {"ro": (2, 0x1FE0000), "rw": (3, 0x1FF0000), "rw2": (4, 0x1FF8000)}
FAR_CODE = "ro"
