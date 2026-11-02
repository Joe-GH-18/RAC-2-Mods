# The Portal Gun for Ratchet & Clank 2 HD

The portal gun from Portal in Ratchet & Clank 2, in the PS3 HD version on the European Trilogy disc
(**BCES01503**). Two portals on the level's surfaces, each a live view of what is at the other one,
and you keep your momentum going through: fall into a portal on the floor and you fly out of the one
on the wall.

| Control | What it does |
|---|---|
| Triangle | Quick Select: the Portal Gun has a slot of its own. Pick it to take it out, pick any other weapon to put it away. With it out, two bars at the bottom of the screen light up blue and orange once that portal is placed |
| L1 | Aim. With the gun out there is a blue and orange crosshair, and the shot goes through its middle |
| Circle | Shoot the blue portal |
| Square | Shoot the orange portal |

- A portal goes where the camera is looking, along the middle of the screen: a shot flies there from his hand, and the portal opens when it arrives. The old one stays until then.
- While the gun is out, Circle and Square do nothing else: no ammunition is used and the wrench stays
  put. Put the gun away and the weapon in Ratchet's hand is back as it was.
- With the gun out the HUD's weapon panel is hidden; the weapon behind it comes back with its ammunition as it was.
- The gun takes the Clank Zapper's place: its tile on the Weapons page, with its own name, icon and picture, and its slot in the Quick Select. Every save owns it from the next level on, and it goes into the first free Quick Select slot. If all eight are taken, put it there on the pause menu's Quick Select page. The Zapper itself is gone while the mod is installed. The gun uses no ammunition.
- With one portal up it is a solid disc; with both up you can see through them.

Everything was made and tested on RPCS3 under Linux. It has not been tried on a console.

## Patching the game

You need Python 3 and RC2's **decrypted** executable: in RPCS3, *Utilities > Decrypt PS3 Binaries*
on `PS3_GAME/USRDIR/RC2.ppu.self` of the Trilogy gives you `RC2.ppu.elf`.

```
python patch.py /path/to/RC2.ppu.elf
```

Answer its questions. The first choice for the target replaces `RC2.ppu.self` next to the file and
keeps the original as `RC2.ppu.self.bak`. Without questions:
`python patch.py RC2.ppu.elf -o /path/to/USRDIR/RC2.ppu.self`.

Then close RPCS3 completely and **boot the Trilogy, choosing Ratchet & Clank 2 on its menu**. With the
mod installed, booting `RC2.ppu.self` directly works as well.

The patcher only accepts the one executable it was made for (it compares checksums).

**To undo it**, copy `RC2.ppu.self.bak` back over `RC2.ppu.self`.

## Shooting the moon

Five levels have a moon or planet in the sky (2, 7, 19, 20 and 26). Shoot a portal at it, then the other
one anywhere: that one opens on space and pulls in Ratchet, enemies, shots and crates near it, faster the
closer they are. It stays open until you shoot a new portal or leave the level. Ratchet dies of it as of a
fall and is left alone for ten seconds after coming back, so move away if he comes back beside it; what else
goes out is gone for the rest of the level. Portals stay when he dies, this pair or any other.

## Limits

- Ratchet, enemies and weapon shots go through. Crates, bolts and everything else do not, and the wall behind a portal stays solid for them.
- To fire a weapon through a portal, pick that weapon: the portals stay, but while the gun is out Circle shoots portals.
- Every weapon that fires something now works through a portal: thrown and flying things go through (Lancer, Minirocket Tube, RYNO, Chopper, Seeker Gun, Plasma Coil, Bouncer, Hoverbomb, Gravity Bomb, Bomb Glove, Visibomb, Miniturret Glove, Decoy Glove, and the Spiderbot walks through), and those that hit along a line go on from the other portal (Pulse Rifle, Blitz Gun, Tesla Claw), as do the Lava Gun's droplets. An enemy on the far side takes the damage. The picture of a beam is the exception: it is drawn straight, and ends in the wall when what it hit is in the other room.
- The Sheepinator does not work through a portal: its beam reaches the enemy, but it does not turn into a sheep.
- The Walloper (a punch), the Zodiac (the whole screen), the Shield Charger and the Synthenoids (they stay around Ratchet) have nothing that could go through.
- Enemies that walk onto a floor portal drop through it and fly out of the other one until they land. This was tried with a few enemies, not every kind; one forced through while asleep and far away stayed frozen in the air.
- Between two walls Ratchet can stop halfway, on either side, and step back; the right stick sends the camera on through. With a floor and a ceiling he drops in and falls on through the pair, for ever if you let him: steer to get out. With a wall and a floor, or two floors, he goes in the same way but comes out flying, with no stopping halfway.
- A moon counts by its height in the sky, as some skies turn: open sky at the same height counts as the moon too.
- It was tried in all 27 level slots, by jumping to each from a running game, but nobody has played through
  the game with it, and it has not been tried with a real controller. Levels in the starship and as Giant Clank keep their own controls: the gun does nothing there.
- With two portals up and in view the whole level is drawn twice a frame, one portal's view at a time, so each
  view updates at half the frame rate. A portal out of view costs nothing.
- For about three frames of going through a portal the very edge of the screen can show a thin dark band, and a portal close to the camera at the screen's edge can show streaks in its outer part.
- The texts are in English in every language.

## What is in here

- `patch.py`: the patcher. Plain Python, no packages needed.
- `patches/`: the patch file. It holds the mod's own code and model, no game data.
- `mods/portal.py`: the mod, with what it does at the top. `mods/gunmesh.py`, `gunicon.py` and `gunpicture.py` draw the gun, its icon and its picture from code.
- `build.py`: assembles the mod and writes the patched executable and the patch file.
- `tools/`: what it was found and tested with.
- `NOTES.md`: everything found out about the game, and how far each thing is confirmed.

## Building from source

```
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
RC2_ELF=/path/to/RC2.ppu.elf .venv/bin/python build.py --export
```

That writes `build/RC2.elf` and the patch file. `--install` also replaces `RC2.ppu.self` next to the
input. Instead of the environment variable, the path can go into a file `rc2_elf.path`.

## Licence

The code in this repository is under the Apache License 2.0, see `LICENSE`. It contains no data of
the games. Ratchet & Clank is a trademark of Sony Interactive Entertainment and Portal of Valve; this
project is not affiliated with either, nor with Insomniac Games.
