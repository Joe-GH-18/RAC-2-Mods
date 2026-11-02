#!/usr/bin/env python3
"""Launch RPCS3 with RC2 and log the game's state by reading guest memory.

RPCS3 has to be our child: with kernel.yama.ptrace_scope=1 only descendants are readable. It also
answers tools/peek.py: lines in build/cmd are run against guest memory, answers go to build/cmd.out
("r <addr> <len>" reads, "w <addr> <hex bytes>" writes, addresses in hex).
"""
import os
import struct
import subprocess
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ppu import RC2_ELF  # noqa: E402
from mods.game import FRAME_COUNTER, GAME_MODE, HERO, STATE as MOD_STATE  # noqa: E402

# The emulator: the environment variable RPCS3, or the first line of the file rpcs3.path next to
# build.py (not part of the repository), or "rpcs3" from the search path.
RPCS3 = os.environ.get("RPCS3") or "rpcs3"
try:
    with open(os.path.join(ROOT, "rpcs3.path")) as _f:
        RPCS3 = os.environ.get("RPCS3") or _f.readline().strip() or RPCS3
except OSError:
    pass
# The disc's EBOOT.BIN, not RC2.ppu.self: RC2 reads its name from the arguments the Trilogy's menu
# gives it and crashes on a null pointer when booted directly (NOTES.md).
GAME = os.path.join(os.path.dirname(RC2_ELF), "RC2.ppu.self")
SIG_VA, SIG = 0x10200, bytes.fromhex("f821ff917c0802a6")
HERO_STATE = HERO + 0x2294


def descendants(pid):
    out, todo = [], [pid]
    while todo:
        p = todo.pop()
        out.append(p)
        try:
            for t in os.listdir(f"/proc/{p}/task"):
                todo += [int(c) for c in open(f"/proc/{p}/task/{t}/children").read().split()]
        except OSError:
            pass
    return out


def find_guest(root):
    for pid in descendants(root):
        try:
            maps = open(f"/proc/{pid}/maps").read().splitlines()
            mem = open(f"/proc/{pid}/mem", "rb", buffering=0)
        except OSError:
            continue
        for line in maps:
            start = int(line.split("-")[0], 16)
            if start & 0xFFFF or start >= 1 << 62:
                continue
            try:
                mem.seek(start + (SIG_VA & 0xFFFF))
                if mem.read(8) == SIG:
                    return pid, mem, start - (SIG_VA & ~0xFFFF)
            except (OSError, OverflowError, ValueError):
                pass
        mem.close()
    return None


def main():
    proc = subprocess.Popen([RPCS3, *sys.argv[1:], GAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    found = None
    while proc.poll() is None and not found:
        time.sleep(1)
        found = find_guest(proc.pid)
    if not found:
        sys.exit("emulator exited before the game was mapped")
    pid, mem, base = found
    print(f"guest memory of pid {pid} at {base:#x}", flush=True)

    def rd(va, fmt):
        mem.seek(base + va)
        return struct.unpack(">" + fmt, mem.read(struct.calcsize(fmt)))[0]

    here = os.path.join(ROOT, "build")
    cmd_path, out_path, cmd_seen = os.path.join(here, "cmd"), os.path.join(here, "cmd.out"), 0.0
    try:
        cmd_seen = os.path.getmtime(cmd_path)     # commands left from an earlier game are not for this one
    except OSError:
        pass
    wmem = open(f"/proc/{pid}/mem", "r+b", buffering=0)

    def run_commands():
        nonlocal cmd_seen
        try:
            stamp = os.path.getmtime(cmd_path)
        except OSError:
            return
        if stamp <= cmd_seen:
            return
        cmd_seen = stamp
        with open(out_path, "w") as out:
            for line in open(cmd_path).read().splitlines():
                parts = line.split()
                try:
                    if parts and parts[0] == "r":
                        mem.seek(base + int(parts[1], 16))
                        out.write(f"{parts[1]} {mem.read(int(parts[2], 0)).hex()}\n")
                    elif parts and parts[0] == "w":
                        wmem.seek(base + int(parts[1], 16))
                        wmem.write(bytes.fromhex(parts[2]))
                        out.write(f"{parts[1]} written\n")
                except (OSError, ValueError, IndexError) as exc:
                    out.write(f"{line} failed: {exc}\n")
            out.write("done\n")

    t0, last = time.time(), None
    while proc.poll() is None:
        run_commands()
        try:
            now = (rd(GAME_MODE, "i"), rd(HERO_STATE, "i"))
            if now != last:
                print(f"{time.time() - t0:8.2f}s mode {now[0]} hero state {now[1]:#x} frame {rd(FRAME_COUNTER, 'i')}"
                      f" mod frames {rd(MOD_STATE, 'i')}", flush=True)
                last = now
        except (OSError, struct.error):
            pass
        time.sleep(0.05)
    print("emulator closed", flush=True)


if __name__ == "__main__":
    main()
