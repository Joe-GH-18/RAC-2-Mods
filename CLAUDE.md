# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Mods for **Ratchet & Clank 2 HD**, PS3 Trilogy disc (BCES01503), patched into `RC2.ppu.elf` and run on RPCS3. Not PS2 hardware: this is PPC64 (32-bit pointers) with an RSX renderer. The framework comes from the sibling project `../Boxbreaker RAC1` (the same tools for RC1); its `NOTES.md` is the deepest source on shared engine structures and lists RC2 counterparts of many RC1 addresses.

`NOTES.md` here holds the RC2 findings and how far each one is confirmed. Read it before reverse-engineering anything.

## Commands

```
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python build.py                  # build build/RC2.elf
.venv/bin/python build.py --install        # ...and replace RC2.ppu.self in the disc dump (original kept as .bak)
.venv/bin/python build.py --export         # ...and write patches/ for patch.py
SHOW=1 .venv/bin/python build.py           # ...and print the cave's disassembly

.venv/bin/python tools/ingame.py --restart [--level N] # close RPCS3, boot RC2 straight into a level, no save loaded
.venv/bin/python tools/peek.py "r 1fd1100 4, w 1fd1104 00000001"   # read/write guest memory of the running game
.venv/bin/python tools/press.py start:0.6 wait:1 cross             # press buttons, inside the game (see Pitfalls)
.venv/bin/python tools/show.py b0f908 b0f960                       # disassemble the untouched ELF
.venv/bin/python tools/fullsave.py                                  # copy save slot B to a new slot C with all planets and weapons
```

There are no automated tests. A change is verified by building, running it, reading memory with `peek.py` and capturing the window (`import` needs no focus):
`import -window $(xdotool search --name 'FPS:' | tail -1) out.png`.

Machine paths are in the untracked files `rc2_elf.path` and `rpcs3.path`.

## Architecture

- `build.py` assembles every mod in `mods/` into a code cave and turns game instructions into calls of them; `patch.py` applies the same patches with no dependencies. `mods/__init__.py` documents what a mod module must contain. `mods/game.py` holds shared addresses, the cave, the state block and the data segments.
- `tools/trace.py` must be RPCS3's parent process (`ptrace_scope=1`) to reach guest memory; `tools/peek.py` talks to it through `build/cmd`. `tools/ingame.py` starts both, with `--no-gui` and RPCS3's input profile `Backport` (`tools/inputprofile.py`), which leaves the user's `Default.yml` alone. The state block (`game.STATE`) is writable live, so put tuning values there: mod constants are read-only and every rebuild needs a restart.
- `mods/portal.py` is the mod: hooks on PreDraw's entry and the pad read, three that take the wall away for Ratchet in an opening, two for booting without the Trilogy's menu, and the ones that make the gun an item in the Clank Zapper's place (text lookup, the Quick Select's pick, the eight reads of the weapon pictures), all in shared code. Enemies and shots go through from `pt_mobys`, which walks the moby table. The hidden frame (a whole Begin/PreDraw/End with no flip, into a surface of ours) is what makes portals see-through; `NOTES.md` explains it. All its tuning values are in the state block from `+0x180`. `mods/gunmesh.py` builds the gun's mesh and texture, `mods/gunicon.py` its icon, `mods/gunpicture.py` its Weapons page picture from that mesh.
- RC2's hero code exists once per level (24 copies), the engine once (from about `0xb00000`). Keep mod logic in shared code hooks; a per-level hook has to be found and placed in every copy.

## Pitfalls

- **Unpatched, RC2 must boot through the Trilogy's `EBOOT.BIN`:** it takes its name and region from the menu and crashes without them. With the mod installed `pt_name` and `pt_region` stand in, and `tools/ingame.py` boots `RC2.ppu.self` directly.
- **No uinput pads:** a virtual pad is a device for every program on the machine, and it broke the game the user was playing. `tools/press.py` writes buttons into the state block (`+0x418`) and `pt_pad` hands them to the game. RPCS3's own overlays (save screens) read pads inside the emulator and cannot be pressed this way, so tests go to a level with the game's "go to level" instead of loading a save. Keys sent to the window do not work either.
- Never overwrite `RC2.ppu.elf`: it is the build's untouched input (checked by md5). Only `RC2.ppu.self` is replaced.
- `keystone` here needs bare register numbers: `std 0, 0x80(1)`, not `std r0, 0x80(r1)`. A wrong operand makes `KS.asm` return `None`.
- RPCS3 loads system modules from `0x2000000`; nothing of ours may be mapped there.
- The main heap's address changes between boots (`0x40000000`, `0x50000000`): never hard-code one. Only RSX memory (`0xc0000000`) is fixed.
- Keep state block offsets apart: a 0x60-byte copy over the mod's flags once corrupted the heap limit. `mods/portal.py`'s docstring is the map of the block.
- Every level change autosaves into the loaded slot. Back up `NPEA00386_RC2_SAVEDATA_*` before a test that travels (`NOTES.md`, Levels) and restore it with RPCS3 closed.
- Judge rendering from screenshots, several in a row: FPS, memory and the log all looked clean while most levels were garbled, and one good shot once misled.
- Hand-placing a test: portals are just state words, so `peek.py` can put a perfect pair anywhere without aiming.
- Tests take the gun out with `w 1fd1504 00000001` (`+0x404`), or by the Quick Select: hold Triangle, left stick, let go; the weapon's model must have loaded first, so hold about a second. A menu cursor is the left stick. Info popups in the museum swallow Triangle.
- `li` takes at most 32767: a bigger constant is `Invalid operand`, as is any other wrong operand. A branch out of the code cave has to be a `b`, not a conditional one.
- Test walls in the Insomniac Museum (level 21): flat, level floor. A portal needs a real wall to prove anything; level 13's "walls" near the start are a step and a vendor (a moby).
- A moby from the table is not safe to touch by a pattern: junk slots look like mobys, and guesses about what a class keeps in its variables crashed the game twice (a handle taken for a vector, a bolt's target zeroed). Say which kinds and fields are known.
- Do not use `pkill -f` with a pattern that appears in your own command line: it kills your shell. Close RPCS3 with `pkill -TERM -x AppRun.wrapped`.
- Ask before restarting RPCS3 if the user may be playing: a restart loses unsaved progress.
