"""show.py <start> [end]: disassemble a range (hex addresses) of the untouched RC2.ppu.elf."""
import sys

from ppu import Elf, RC2_ELF, show

show(Elf(RC2_ELF), int(sys.argv[1], 16), int(sys.argv[2], 16) if len(sys.argv) > 2 else None)
